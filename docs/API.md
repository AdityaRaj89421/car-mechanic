# API Reference — AI Car Mechanic

Base URL (local dev): `http://localhost:8000`  
Base URL (production): `http://13.53.129.1`

All request bodies are JSON unless noted. All responses are JSON.  
**No authentication required** (MVP scope — add token auth before multi-user production use).

---

## Error contract

No endpoint ever returns a raw 500 or Python traceback. All errors are structured:

```json
{ "field_name": "Human-readable error message." }
```

or for Gemini failures:

```json
{ "ai_status": "error", "reply": "I'm having trouble connecting to the AI service right now." }
```

HTTP status codes used: `200`, `201`, `400`, `404`, `405`, `415`.

---

## Endpoints

### 1. `POST /api/chat/`

Send a user message and receive an AI response. Starts a new conversation if no `conversation_id` is supplied.

#### Request

```json
{
  "message": "My 2019 Toyota Camry makes a loud knocking noise when I accelerate.",
  "conversation_id": 42
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `message` | string | ✅ | Must be non-empty |
| `conversation_id` | integer | ❌ | Omit to start a new conversation |

#### Response `200 OK`

```json
{
  "conversation_id": 42,
  "user_message_id": 101,
  "assistant_message_id": 102,
  "ai_status": "need_more_info",
  "reply": "How many miles are on the engine, and when was the last oil change?",
  "question": "How many miles are on the engine, and when was the last oil change?",
  "diagnosis": null
}
```

| Field | Type | Notes |
|---|---|---|
| `conversation_id` | integer | Use this in all subsequent requests |
| `user_message_id` | integer | DB id of the saved user message |
| `assistant_message_id` | integer | DB id of the saved assistant message |
| `ai_status` | string | `need_more_info` \| `diagnosis_ready` \| `off_topic` \| `error` |
| `reply` | string | Text to display in the chat bubble |
| `question` | string\|null | Populated only when `ai_status == "need_more_info"` |
| `diagnosis` | object\|null | Populated only when `ai_status == "diagnosis_ready"` (see Diagnosis shape below) |

When `ai_status == "diagnosis_ready"`, `diagnosis` contains:

```json
{
  "id": 7,
  "diagnosis_text": "Rod bearing failure due to oil starvation.",
  "symptoms": "Loud knocking on acceleration, 180k miles, overdue oil change.",
  "recommendation": "Stop driving immediately. Tow to a mechanic for engine inspection.",
  "created_at": "2026-09-25T10:00:00Z"
}
```

#### Example `curl`

```bash
# New conversation
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "My car makes a knocking noise when I accelerate"}'

# Continue existing conversation
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "About 180,000 miles, last oil change was 2 years ago", "conversation_id": 42}'
```

#### Error responses

| Condition | Status | Body |
|---|---|---|
| Missing / blank `message` | `400` | `{"message": "This field is required and must not be blank."}` |
| Non-integer `conversation_id` | `400` | `{"conversation_id": "Must be a valid integer."}` |
| Unknown `conversation_id` | `400` | `{"conversation_id": "Conversation 99 does not exist."}` |

---

### 2. `GET /api/chat/<conversation_id>/history/`

Retrieve all messages in a conversation, oldest first. Use on page reload to repopulate chat history.

#### Response `200 OK`

```json
{
  "conversation_id": 42,
  "messages": [
    {
      "id": 101,
      "role": "user",
      "content": "My car makes a knocking noise when I accelerate",
      "media": null,
      "media_type": "none",
      "created_at": "2026-09-25T09:55:00Z"
    },
    {
      "id": 102,
      "role": "assistant",
      "content": "How many miles are on the engine, and when was the last oil change?",
      "media": null,
      "media_type": "none",
      "created_at": "2026-09-25T09:55:01Z"
    }
  ]
}
```

#### Example `curl`

```bash
curl http://localhost:8000/api/chat/42/history/
```

#### Error responses

| Condition | Status |
|---|---|
| Unknown `conversation_id` | `404` |

---

### 3. `POST /api/upload/`

Upload a media file (image, audio, or video). Images are analysed by Gemini and trigger an assistant reply. Audio and video are stored and acknowledged (not sent to Gemini — see scope note below).

**Content-Type:** `multipart/form-data`

#### Request fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | ✅ | The media file |
| `conversation_id` | integer | ✅ | Must be an existing conversation |
| `media_type` | string | ✅ | `"image"` \| `"audio"` \| `"video"` |

#### File constraints

| `media_type` | Extensions | Max size |
|---|---|---|
| `image` | `.jpg` `.jpeg` `.png` `.webp` | 5 MB |
| `audio` | `.mp3` `.wav` `.m4a` | 10 MB |
| `video` | `.mp4` `.mov` | 25 MB |

#### Response `201 Created`

```json
{
  "message": {
    "id": 103,
    "role": "user",
    "content": "[image attachment: engine.jpg]",
    "media": "http://localhost:8000/media/chatbot/messages/engine.jpg",
    "media_type": "image",
    "created_at": "2026-09-25T09:56:00Z"
  },
  "assistant_reply": {
    "id": 104,
    "role": "assistant",
    "content": "I can see significant oil residue around the valve cover gasket. This suggests a gasket leak which could be causing the knocking if oil level has dropped. How long have you noticed this?",
    "media": null,
    "media_type": "none",
    "created_at": "2026-09-25T09:56:02Z"
  }
}
```

> **Scope note:** Audio and video are stored but **not sent to Gemini** in this version. The assistant acknowledges receipt and asks the user to describe the issue in text. Image analysis via Gemini vision is fully implemented.

#### Example `curl`

```bash
curl -X POST http://localhost:8000/api/upload/ \
  -F "file=@/path/to/engine.jpg" \
  -F "conversation_id=42" \
  -F "media_type=image"
```

#### Error responses

| Condition | Status | Body |
|---|---|---|
| Missing file | `400` | `{"file": "A file is required."}` |
| Wrong extension | `400` | `{"file": "Invalid extension '.gif'. Allowed: .jpg, .jpeg, .png, .webp."}` |
| File too large | `400` | `{"file": "File too large (6.2 MB). Max for image: 5 MB."}` |
| Invalid `media_type` | `400` | `{"media_type": "Must be one of: image, audio, video."}` |
| Missing `conversation_id` | `400` | `{"conversation_id": "This field is required."}` |

---

### 4. `POST /api/diagnosis/`

Retrieve the existing diagnosis for a conversation, or attempt to derive one from the conversation history if none exists yet.

#### Request

```json
{ "conversation_id": 42 }
```

#### Response `200 OK`

```json
{
  "source": "existing",
  "diagnosis": {
    "id": 7,
    "diagnosis_text": "Rod bearing failure due to oil starvation.",
    "symptoms": "Loud knocking on acceleration, 180k miles, overdue oil change.",
    "recommendation": "Stop driving immediately. Tow to a mechanic for engine inspection.",
    "created_at": "2026-09-25T10:00:00Z"
  },
  "message": null
}
```

| `source` value | Meaning |
|---|---|
| `"existing"` | A Diagnosis row already exists — returned as-is |
| `"derived"` | No prior diagnosis; Gemini produced one from the history |
| `"insufficient_data"` | Gemini needs more info before diagnosing |
| `"error"` | AI unavailable |

#### Example `curl`

```bash
curl -X POST http://localhost:8000/api/diagnosis/ \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": 42}'
```

---

### 5. `POST /api/booking/`

Create a service booking. Automatically links the latest Diagnosis for the conversation if one exists.

#### Request

```json
{
  "conversation_id": 42,
  "customer_name": "Aditya Raj",
  "customer_contact": "aditya@example.com",
  "car_model": "2019 Toyota Camry",
  "issue_summary": "Loud knocking noise on acceleration — suspected rod bearing failure",
  "service": "Full engine inspection and oil system diagnostics"
}
```

| Field | Type | Required |
|---|---|---|
| `conversation_id` | integer | ✅ |
| `customer_name` | string | ✅ |
| `customer_contact` | string | ✅ |
| `car_model` | string | ✅ |
| `issue_summary` | string | ✅ |
| `service` | string | ✅ |

#### Response `201 Created`

```json
{
  "id": 3,
  "conversation_id": 42,
  "customer_name": "Aditya Raj",
  "customer_contact": "aditya@example.com",
  "car_model": "2019 Toyota Camry",
  "issue_summary": "Loud knocking noise on acceleration — suspected rod bearing failure",
  "service": "Full engine inspection and oil system diagnostics",
  "status": "pending",
  "diagnosis": {
    "id": 7,
    "diagnosis_text": "Rod bearing failure due to oil starvation.",
    "symptoms": "...",
    "recommendation": "...",
    "created_at": "2026-09-25T10:00:00Z"
  },
  "created_at": "2026-09-25T10:05:00Z"
}
```

#### Example `curl`

```bash
curl -X POST http://localhost:8000/api/booking/ \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": 42,
    "customer_name": "Aditya Raj",
    "customer_contact": "aditya@example.com",
    "car_model": "2019 Toyota Camry",
    "issue_summary": "Knocking noise, suspected rod bearing failure",
    "service": "Engine inspection"
  }'
```

#### Error responses

| Condition | Status | Body |
|---|---|---|
| Any required field missing | `400` | `{"field_name": "This field is required."}` |
| Unknown `conversation_id` | `400` | `{"conversation_id": "Conversation 99 does not exist."}` |

---

### 6. `GET /api/booking/<booking_id>/`

Retrieve a booking with its nested Diagnosis and Conversation summary.

#### Response `200 OK`

Same shape as the `POST /api/booking/` response body above.

#### Example `curl`

```bash
curl http://localhost:8000/api/booking/3/
```

#### Error responses

| Condition | Status |
|---|---|
| Unknown `booking_id` | `404` |

---

## Gemini Response Contract

The `services/gemini.py` module always returns one of these shapes — never raises an exception:

```jsonc
// Status 1: needs more information
{ "status": "need_more_info", "question": "When did you last change the oil?" }

// Status 2: diagnosis complete
{
  "status": "diagnosis_ready",
  "diagnosis": "Rod bearing failure due to oil starvation.",
  "symptoms": "Knocking at acceleration, 180k miles, no recent oil change.",
  "recommendation": "Stop driving. Tow to mechanic immediately."
}

// Status 3: off-topic query
{ "status": "off_topic", "message": "I can only help with vehicle-related questions." }

// Status 4: AI unavailable (network error, bad key, quota, etc.)
{ "status": "error", "error": "ai_unavailable: ServiceUnavailable" }
```
