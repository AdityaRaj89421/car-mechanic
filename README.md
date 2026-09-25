# AI Car Mechanic

> An AI-powered car mechanic assistant. Describe your car problem via **text, image, audio, or video** — the assistant diagnoses the issue using Google Gemini, explains it in plain language, and helps you book a service appointment, all through a conversational chat interface.

**Live URLs**
- Frontend: _deploy to Vercel (see Stage 7 instructions)_
- Backend API: `http://13.53.129.1` (EC2 t2.micro, Stockholm region)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router, TypeScript, React 19) |
| Backend | Django 4.2 + Django REST Framework |
| AI | Google Gemini (`gemini-3.6-flash`) via `google-genai` SDK |
| Database | SQLite (local dev & MVP); PostgreSQL-ready |
| Media storage | Django `MEDIA_ROOT` (local disk / EC2 EBS) |
| Production serving | Gunicorn + WhiteNoise + nginx |
| Deployment | Vercel (frontend) · AWS EC2 t2.micro (backend) |

---

## Project Structure

```
ai-car-mechanic/
├── backend/                   Django project
│   ├── carmechanic/           Project settings, URLs, WSGI/ASGI
│   ├── chatbot/               Main app — models, views, serializers, tests
│   ├── services/
│   │   └── gemini.py          Gemini AI wrapper (the ONLY place that calls the API)
│   ├── scripts/
│   │   └── ec2_bootstrap.sh   One-shot EC2 setup script
│   ├── gunicorn.conf.py       Production Gunicorn config
│   ├── Procfile               Heroku-style process definition
│   ├── requirements.txt
│   ├── .env.example           Local dev env template
│   └── .env.production.example  Production env template
├── frontend/                  Next.js app
│   ├── src/
│   │   ├── app/               Next.js App Router pages + error boundaries
│   │   ├── components/        ChatShell, MessageBubble, DiagnosisCard, BookingModal, …
│   │   ├── hooks/useChat.ts   useReducer state machine for chat
│   │   ├── lib/api.ts         Centralised API client (single source of truth)
│   │   ├── services/          Upload service (XHR for progress events)
│   │   └── types/             Shared TypeScript types
│   ├── vercel.json
│   └── .env.local.example
├── docs/
│   ├── API.md                 Full endpoint reference
│   └── ARCHITECTURE.md        System design & Gemini boundary explanation
├── CONTRIBUTING.md            Credential hygiene rules
└── README.md                  ← you are here
```

---

## Local Development Setup

### Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.11 |
| Node.js | 18 |
| npm | 9 |
| Git | any |

---

### 1 — Clone the repo

```bash
git clone https://github.com/AdityaRaj89421/car-mechanic.git
cd car-mechanic
```

---

### 2 — Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
```

Edit `backend/.env` and fill in the two required values:

```dotenv
DJANGO_SECRET_KEY=any-long-random-string-50-chars
GEMINI_API_KEY=your-google-ai-studio-api-key
```

```bash
# Run database migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

API is now available at **http://localhost:8000**

To confirm it's working:
```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "My car makes a knocking noise"}'
```

---

### 3 — Frontend

Open a second terminal:

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.local.example .env.local
# Default value is already correct for local dev:
#   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Start the dev server
npm run dev
```

App is now available at **http://localhost:3000**

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | ✅ | — | Django secret key (50+ random chars) |
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio API key |
| `DEBUG` | ❌ | `True` | Set to `False` in production |
| `ALLOWED_HOSTS` | ❌ | `localhost,127.0.0.1` | Comma-separated list of allowed hosts |
| `FRONTEND_ORIGIN` | ❌ | `http://localhost:3000` | Frontend URL(s) for CORS |
| `SECURE_SSL_REDIRECT` | ❌ | `True` (prod only) | Set `False` when nginx handles redirects |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | `http://localhost:8000` | Backend API base URL |

---

## Running Tests

```bash
cd backend
# With venv active:
python manage.py test chatbot --verbosity=2
```

**41 tests, 0 failures.** Covers: chat happy path, off-topic rejection, upload validation (wrong type, oversized), booking creation & retrieval, and the no-500 contract across all endpoints.

All Gemini calls are mocked — no real API calls or quota used.

---

## Running in Production (EC2)

See [`backend/scripts/ec2_bootstrap.sh`](backend/scripts/ec2_bootstrap.sh) for the full automated setup, and [`backend/.env.production.example`](backend/.env.production.example) for required production env vars.

Key differences from local dev:
- `DEBUG=False`
- Gunicorn serves the Django app (not `runserver`)
- WhiteNoise serves static files
- nginx acts as reverse proxy on port 80
- SQLite DB persists on EBS root volume (lost only if instance is **terminated**, not rebooted)

---

## Key Design Decisions

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full architecture explanation, including the **deterministic-logic-vs-Gemini boundary** (an explicit evaluation criterion).

---

## API Reference

See [`docs/API.md`](docs/API.md) for the full endpoint reference with request/response shapes and example `curl` calls.

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) — especially the **mandatory credential hygiene rules**: real API keys are never written into any tracked file.
