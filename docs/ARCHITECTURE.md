# Architecture — AI Car Mechanic

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User's Browser                           │
│                                                                 │
│   Next.js Frontend (Vercel)                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│   │  ChatShell   │  │DiagnosisCard │  │   BookingModal       │ │
│   │  useChat()   │  │              │  │                      │ │
│   └──────┬───────┘  └──────────────┘  └──────────────────────┘ │
│          │ lib/api.ts (all HTTP calls centralised here)         │
└──────────┼──────────────────────────────────────────────────────┘
           │ HTTPS  (CORS: FRONTEND_ORIGIN env var)
           ▼
┌──────────────────────────────────────────────────────────────────┐
│            Backend  (AWS EC2 t2.micro, nginx + gunicorn)        │
│                                                                  │
│  nginx (port 80)                                                 │
│    └─► gunicorn → Django (carmechanic project)                   │
│              │                                                   │
│         chatbot/views.py   ← deterministic logic lives here      │
│              │                                                   │
│    ┌─────────┼──────────────────────────────────────┐           │
│    │         │         DETERMINISTIC BOUNDARY        │           │
│    │         ▼                                       │           │
│    │   services/gemini.py   ← only file that calls   │           │
│    │         │               the Gemini API          │           │
│    │         ▼                                       │           │
│    │   Google Gemini API (gemini-3.6-flash)          │           │
│    └─────────────────────────────────────────────────┘           │
│                                                                  │
│   SQLite (db.sqlite3 on EBS)                                     │
│   MEDIA_ROOT (uploads on EBS)                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## The Deterministic-Logic-vs-Gemini Boundary

This is the most important architectural decision in the system and an explicit evaluation criterion.

### The Rule

> **Deterministic business logic lives in `chatbot/views.py` and the Django models. The Gemini API is called only through `services/gemini.py`. These two layers never bleed into each other.**

### What is deterministic (Django layer)

All of the following happen in Python, with no AI involvement:

| Operation | Where | Why deterministic |
|---|---|---|
| Input validation (blank message, missing fields) | `views.py` | Business rule — always the same answer |
| File validation (type, extension, size) | `views.py` | Hard limits — not a judgment call |
| Conversation creation / lookup | `views.py` | DB operation |
| Saving user `Message` rows | `views.py` | DB operation |
| Saving assistant `Message` rows | `views.py` | DB operation |
| Saving `Diagnosis` rows | `views.py` | DB operation |
| Booking validation and creation | `BookingCreateSerializer` | Business rule |
| Auto-linking Diagnosis to Booking | `BookingCreateSerializer` | FK lookup |
| History retrieval (ordered messages) | `views.py` | DB query |
| HTTP status codes (400, 404, etc.) | `views.py` | Protocol — not AI's decision |
| Error responses to the client | `views.py` | Always structured JSON |

### What is non-deterministic (Gemini layer)

Only these decisions are delegated to the AI:

| Decision | Why AI |
|---|---|
| "Do I have enough information to diagnose?" | Requires clinical judgment across free-text |
| "What follow-up question should I ask?" | Context-dependent, open-ended |
| "What is the diagnosis, symptoms, recommendation?" | Domain expertise + natural language synthesis |
| "Is this query off-topic?" | Semantic classification |
| Visual analysis of an uploaded image | Computer vision |

### Why this boundary matters

**Predictability**: Every HTTP 400 you ever get is because of a validation rule in Python code — not because Gemini decided to return a different JSON shape. You can write unit tests that never touch the network.

**Testability**: The 41-test suite achieves 100% endpoint coverage with Gemini fully mocked (`unittest.mock.patch`). No real API calls, no quota consumed, deterministic results.

**Graceful degradation**: If Gemini is down (503, quota exceeded, bad key), the Django layer catches the error in `services/gemini.py` and returns `{"status": "error"}`. The frontend shows a friendly message. No 500, no crash, no data loss.

**Cost control**: The boundary makes it trivially easy to add rate-limiting, caching, or fallback behaviour around the one function that costs money (`call_gemini`).

---

## Data Flow — Chat Turn

```
User types message
        │
        ▼
Frontend: lib/api.ts → POST /api/chat/ {message, conversation_id}
        │
        ▼
views.chat()
  ├─ Validate message (non-empty)                [deterministic]
  ├─ Resolve or create Conversation              [deterministic]
  ├─ Save user Message row                       [deterministic]
  ├─ Build history list from DB                  [deterministic]
  │
  ├─► services/gemini.call_gemini(history)       [AI boundary ─────────────┐]
  │       │                                                                 │
  │       ├─ Construct Gemini contents list                                 │
  │       ├─ POST to Gemini API with system prompt + response_schema        │
  │       ├─ Parse + validate JSON response                                 │
  │       └─ Return {status, question|diagnosis+symptoms+recommendation|    │
  │                  message|error}                                         │
  │                                          [AI boundary ─────────────────┘]
  │
  ├─ Map ai.status → human-readable reply text   [deterministic]
  ├─ Save assistant Message row                  [deterministic]
  ├─ If diagnosis_ready → save Diagnosis row     [deterministic]
  │
  └─► Response 200 {conversation_id, ai_status, reply, diagnosis|null}
        │
        ▼
Frontend: render assistant bubble
         If diagnosis_ready → render DiagnosisCard + "Book Mechanic" button
```

---

## Data Flow — Image Upload

```
User selects image file
        │
        ▼
Frontend: services/api.ts → XHR (for upload progress) → POST /api/upload/
        │
        ▼
views.upload()
  ├─ Validate conversation                       [deterministic]
  ├─ Validate media_type enum                    [deterministic]
  ├─ Validate extension                          [deterministic]
  ├─ Validate MIME type                          [deterministic]
  ├─ Validate file size                          [deterministic]
  ├─ Save user Message row (with media file)     [deterministic]
  │
  ├─ (image only) Read image bytes               [deterministic]
  ├─► services/gemini.call_gemini(               [AI boundary]
  │       history, image_bytes, image_mime)
  │
  ├─ Map ai.status → reply text                  [deterministic]
  ├─ Save assistant Message row                  [deterministic]
  │
  └─► Response 201 {message, assistant_reply}
```

> **Audio/video scope decision**: Audio and video files are stored and acknowledged but NOT sent to Gemini. This was a deliberate decision to minimise API usage and complexity for the MVP. The stored files remain available for a future stage using the Gemini File API.

---

## Models

```
Conversation
    │ 1:N
    ├──► Message (role: user|assistant, media: FileField nullable, media_type: image|audio|video|none)
    │
    ├──► Diagnosis (diagnosis_text, symptoms, recommendation)
    │
    └──► Booking (customer_name, contact, car_model, issue_summary, service, status: pending|confirmed|completed|cancelled)
              │ N:1 (nullable)
              └──► Diagnosis
```

---

## Frontend State Machine

`useChat.ts` uses `useReducer` with these states:

```
IDLE
  │  user sends message
  ▼
SENDING  (optimistic: user bubble appears immediately)
  │  POST /api/chat/ responds
  ├─► IDLE + messages updated
  └─► ERROR (red banner, previous messages intact)

UPLOADING  (XHR progress 0–100%)
  │  POST /api/upload/ responds
  ├─► IDLE + image thumbnail in message list
  └─► ERROR

BOOKING_OPEN  (modal visible)
  │  user submits form
  ├─► BOOKING_SUCCESS (confirmation with booking ID)
  └─► BOOKING_ERROR (field errors shown inline)
```

---

## Security Notes (MVP → Production gaps)

| Area | MVP state | Production requirement |
|---|---|---|
| Authentication | None — any client can access any conversation | DRF Token Auth or session auth; scope all queries to `request.user` |
| Database | SQLite | PostgreSQL (via `dj-database-url` + `psycopg2`) |
| HTTPS | HTTP only (nginx, no TLS) | ACM cert + ALB, or Let's Encrypt + certbot |
| Media storage | Local disk (EBS) | S3 + presigned URLs (via `django-storages`) |
| Secret management | `.env` file on instance | AWS Secrets Manager or Parameter Store |
| Rate limiting | None | `django-ratelimit` or API Gateway throttling |
