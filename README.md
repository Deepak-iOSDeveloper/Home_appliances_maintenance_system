# Autonomous Residential Health and Intelligence System (ARHIS)

ARHIS is the Home Appliances Maintenance System: a full-stack platform for
monitoring home appliances, diagnosing issues, and delivering AI-assisted
troubleshooting. It pairs a Django + DRF backend with a React dashboard and
real-time WebSocket chat.

## Features

- **Digital twin dashboard** for homes, rooms, and devices with health scoring
- **Device discovery** via local mDNS scan
- **Diagnostics** for Matter nodes with anomaly scores and telemetry logs
- **AI troubleshooter** with streaming chat and RAG over uploaded manuals
- **Observability** for agent traces and session performance metrics

## Tech Stack

- **Backend:** Django, Django REST Framework, Channels, Celery
- **AI/RAG:** LangChain, LangGraph, FAISS
- **Frontend:** React, Vite, React Router, Recharts
- **Data:** SQLite (default), Redis (optional for Channels/Celery)

## Project Structure

```
arhis/                 # Django project configuration
apps/                  # Feature apps (dashboard, diagnostics, troubleshooter, observability)
frontend/              # React + Vite client
requirements.txt       # Backend dependencies
```

## Quick Start (Local Development)

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:5173/`.

## Environment Variables

See `.env.example` for defaults.

- `SECRET_KEY` – Django secret key
- `DEBUG` – Django debug flag
- `ALLOWED_HOSTS` – Comma-separated host list
- `DATABASE_URL` – Optional database override (defaults to SQLite)
- `REDIS_URL` – Optional Redis connection string
- `OPENAI_API_KEY` – Optional OpenAI API key for LLM responses
- `CELERY_TASK_ALWAYS_EAGER` – Run Celery tasks inline in dev

## API Overview

All API routes are prefixed with `/api/`.

- `GET /api/dashboard/homes/`
- `GET /api/dashboard/rooms/`
- `GET /api/dashboard/devices/`
- `GET /api/dashboard/health-score/latest/`
- `GET /api/diagnostics/nodes/`
- `GET /api/diagnostics/logs/<node_id>/`
- `GET /api/observability/metrics/`
- `GET /api/observability/metrics/summary/`
- `POST /api/troubleshooter/sessions/`
- `POST /api/troubleshooter/manuals/upload/`

WebSocket chat endpoint:

```
ws://<host>/ws/chat/<session_id>/
```

## Background Workers (Optional)

To run anomaly detection and health scoring asynchronously, start Redis and
run a Celery worker:

```bash
celery -A arhis worker -l info
```

## Optional Dependencies

Some features require extra Python packages:

- **Manual PDF upload:** `pdfplumber`, `pypdfium2`, `easyocr`
- **mDNS network scan:** `zeroconf`

Install them as needed:

```bash
pip install pdfplumber pypdfium2 easyocr zeroconf
```
