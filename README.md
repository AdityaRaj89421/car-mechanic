# AI Car Mechanic

An AI-powered car mechanic assistant that lets users describe their car problems via text, images, audio, or video. The AI diagnoses the issue using Google Gemini, explains it in plain language, and helps the user book a service appointment — all through a conversational chat interface.

---

## Project Structure

```
ai-car-mechanic/
├── backend/    Django + Django REST Framework API
├── frontend/   Next.js (TypeScript, App Router, Tailwind CSS)
├── README.md
└── .gitignore
```

---

## Backend Setup

> Requires Python 3.11+

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in DJANGO_SECRET_KEY and GEMINI_API_KEY

python manage.py migrate
python manage.py runserver
```

API will be available at `http://localhost:8000`.

---

## Frontend Setup

> Requires Node.js 18+

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local if your backend runs on a different port

npm run dev
```

App will be available at `http://localhost:3000`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/` | Send a chat message and receive an AI response |
| POST | `/api/upload/` | Upload media (image / audio / video) |
| POST | `/api/diagnosis/` | Trigger AI diagnosis for a conversation |
| POST | `/api/booking/` | Create a service booking |
| GET | `/api/booking/<id>/` | Retrieve a booking by ID |

---

## Roadmap

- **Stage 1** ✅ — Project scaffold, models, stub routes, frontend shell
- **Stage 2** — Gemini chat integration, streaming responses
- **Stage 3** — Media upload handling, multimodal diagnosis
- **Stage 4** — Booking flow, confirmation, status tracking
