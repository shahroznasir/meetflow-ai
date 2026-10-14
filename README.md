<div align="center">

# ⚡ MeetFlow AI
### Autonomous Meeting Intelligence, Diarization & Action Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-2.0%20Flash-4285F4.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Chrome Extension](https://img.shields.io/badge/Chrome%20Extension-Manifest%20V3-EA4335.svg?logo=googlechrome&logoColor=white)](https://developer.chrome.com/docs/extensions/mv3/intro/)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MeetFlow AI** is an enterprise-grade conversation intelligence platform inspired by modern AI productivity suites like Fireflies.ai. It captures, transcribes, diarizes, and synthesizes multi-speaker discussions across **Google Meet**, **Microsoft Teams**, **Zoom**, audio file uploads, and **Universal IVR / Telephony streams** using **Google Gemini 2.0 & 1.5**.

[Explore Features](#-key-capabilities) • [Architecture](#-architecture-topology) • [Quickstart](#-quickstart-guide) • [Chrome Extension](#-chrome-extension-setup) • [Cloud Deployment](#-cloud-deployment)

---

</div>

## 🌟 Key Capabilities

| Capability | Description |
| :--- | :--- |
| **🎙️ Multi-Speaker Ingestion** | In-browser dual-channel mixing (remote tab audio + host microphone) via a Manifest V3 Chrome Extension. Also supports direct `.mp3`, `.wav`, `.webm` file uploads and 8kHz $\mu$-law telephony streams. |
| **🤖 Gemini 2.0 Synthesis** | Automated extraction of executive summaries, key decisions, speaker talk-time analytics, sentiment breakdown, and high-priority action items. |
| **⚡ Ask Aura AI Co-Pilot** | Interactive chatbot grounded in your meeting transcript. Ask questions like *"Draft a follow-up email"*, *"Extract blockers"*, or *"What did David commit to?"* with exact timestamp citations (`[00:01:24]`). |
| **⏱️ Click-to-Seek Playback** | Synchronized audio player allows you to click any sentence or timestamp in the transcript to jump audio playback instantly with sub-second precision. |
| **📧 Automated Recaps & Calendar Invites** | Dispatches branded HTML meeting recaps to attendees with attached corporate PDF minutes (ReportLab) and calendar `.ics` action item invites. |
| **🔒 Enterprise Privacy** | Zero audio retention leaks, client-side dual-channel mixing, and configurable storage policies. |

---

## 🏗 Architecture Topology

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Chrome Extension (MV3)      │       │   Universal IVR / Phone Stream  │
│  • getDisplayMedia (Tab Audio)  │       │   • Twilio Media Stream (8kHz)  │
│  • getUserMedia (Host Mic)      │       │   • Asterisk / FreeSWITCH (SIP) │
│  • Web Audio API Stereo Mixer   │       │   • Inbound WebSocket Gateway   │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 └───────────────────┬─────────────────────┘
                                     ▼
                   ┌───────────────────────────────────┐
                   │       FastAPI Audio Gateway       │
                   │  • Dual-Channel Volume Balancing  │
                   │  • 16kHz Linear PCM Resampling    │
                   │  • Rate Limiting & Auth Gateway   │
                   └─────────────────┬─────────────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │    Google Gemini 2.0 Flash Core   │
                   │  • Multimodal Audio Understanding │
                   │  • Multi-Speaker Diarization      │
                   │  • Structured Pydantic MoM Schema │
                   └─────────────────┬─────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
  ┌─────────────────────────────┐         ┌─────────────────────────────┐
  │     Persistence Layer       │         │       Dispatch Engine       │
  │ • PostgreSQL 16 + pgvector  │         │ • Branded HTML Email Recap  │
  │ • SQLite (Local Mode)       │         │ • Corporate PDF (ReportLab) │
  │ • MinIO S3 Object Storage   │         │ • Calendar Invites (.ics)   │
  │ • Redis Broker & Cache      │         │ • SMTP / OAuth2 Gateway     │
  └─────────────────────────────┘         └─────────────────────────────┘
```

---

## 📁 Repository Structure

```
meetflow-ai/
├── backend/                         # FastAPI Gemini Backend Engine
│   ├── app/
│   │   ├── main.py                  # API routes, web dashboard & zip packager
│   │   ├── config.py                # Pydantic environment settings
│   │   ├── schemas/mom.py           # Structured output schemas
│   │   ├── db/                      # SQLAlchemy models & connection pool
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   ├── services/
│   │   │   ├── gemini_service.py    # Google Gemini 2.0 multimodal API connector
│   │   │   ├── audio_processor.py   # Telephony decoding & resampling
│   │   │   ├── pdf_service.py       # Corporate PDF MoM generation
│   │   │   └── email_service.py     # HTML email & ICS attachment dispatcher
│   │   ├── templates/
│   │   │   └── index.html           # Fireflies-inspired SPA & Notebook UI
│   │   └── routers/
│   │       ├── meetings.py          # Audio ingestion, transcript RAG, PDF routes
│   │       ├── actions.py           # Action item tracking & status toggles
│   │       └── telephony.py         # Universal IVR / Twilio WebSocket gateway
│   ├── storage/                     # Raw audio recordings & PDF summaries
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── extension/                       # Chrome Extension (Manifest V3)
│   ├── manifest.json                # Permissions (tabCapture, offscreen, storage)
│   ├── popup/                       # Interactive Extension Popup
│   │   ├── popup.html               # Light theme UI, live VU-meter, live bookmarks
│   │   ├── popup.css                # Fireflies SaaS styling & animations
│   │   └── popup.js                 # MediaStream controller & state sync
│   ├── background/                  # Service worker managing audio lifecycle
│   │   └── service_worker.js
│   ├── offscreen/                   # Web Audio API dual-channel stereo mixer
│   │   ├── offscreen.html
│   │   └── offscreen.js
│   ├── content_scripts/             # Meeting DOM scrapers (Meet & Teams)
│   │   ├── meet_observer.js
│   │   └── teams_observer.js
│   └── permission/                  # One-time mic authorization page
│
├── tests/                           # Complete automated test suite (12/12 passing)
│   ├── test_api_endpoints.py
│   ├── test_audio_processor.py
│   ├── test_canonical_pipeline.py
│   ├── test_email_dispatch.py
│   └── test_gemini_mom.py
│
├── docker-compose.yml               # Production infrastructure (Postgres, MinIO, Redis)
├── vercel.json                      # Vercel deployment specification
└── requirements.txt                 # Root dependencies
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
* Python 3.10+
* Google Gemini API Key ([Get one at Google AI Studio](https://aistudio.google.com/))
* Google Chrome, Microsoft Edge, or Brave

### 2. Local Setup

```bash
# Clone the repository
git clone https://github.com/shahroznasir/meetflow-ai.git
cd meetflow-ai/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

Edit `backend/.env` with your API credentials:
```env
GEMINI_API_KEY=AIzaSy...your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
ENVIRONMENT=development
```

### 3. Start the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* **Interactive Web Platform**: [http://localhost:8000](http://localhost:8000)
* **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Direct Extension Download**: [http://localhost:8000/api/v1/extension/download](http://localhost:8000/api/v1/extension/download)

---

## 🧩 Chrome Extension Setup

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** **ON** (switch in top-right corner).
3. Click **Load unpacked** and select the [`extension/`](./extension) folder from this repository.
4. Pin **MeetFlow AI** to your Chrome toolbar.
5. Join any Google Meet or Microsoft Teams call:
   * Click the extension icon.
   * Review detected attendees and meeting title.
   * Click **Start Recording**.
   * Use **In-Call Bookmarks** (`⭐ Decision`, `📌 Action`, `🔥 Blocker`) to mark key moments.
   * Click **Stop & Generate MoM** — Gemini synthesizes the discussion in seconds!

---

## 🐳 Production Deployment with Docker Compose

To run the complete production enterprise stack including **PostgreSQL 16 (with pgvector)**, **MinIO S3 storage**, **Redis**, and **Mailpit** (local SMTP inspector):

```bash
docker-compose up -d --build
```

| Service | Address | Description |
| :--- | :--- | :--- |
| **MeetFlow AI Web Platform** | `http://localhost:8000` | Full single-page app, Ask Aura, and Notebook |
| **Mailpit Webmail** | `http://localhost:8025` | Inspect recap emails, PDF attachments & `.ics` files |
| **MinIO S3 Console** | `http://localhost:9001` | Object storage browser (`minioadmin` / `minioadminpassword`) |
| **PostgreSQL 16 + pgvector** | `localhost:5432` | Relational database & semantic vector search |

---

## ☁️ Cloud Deployment

### Deploy to Render or Railway (Recommended for AI Audio)
Because AI audio processing involves multi-megabyte payloads and long-running Gemini diarization, **[Render.com](https://render.com)** and **[Railway.app](https://railway.app)** are recommended over serverless platforms:
1. Connect your GitHub repository: `https://github.com/shahroznasir/meetflow-ai`.
2. Set Build Command: `pip install -r requirements.txt`.
3. Set Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
4. Add Environment Variable: `GEMINI_API_KEY`.

### Deploy to Vercel
The repository includes a pre-configured [`vercel.json`](./vercel.json) for Vercel Serverless deployments:
1. Import repository at [vercel.com/new](https://vercel.com/new).
2. Set Environment Variables:
   * `GEMINI_API_KEY` = your API key
   * `ENVIRONMENT` = `production`
   * `STORAGE_DIR` = `/tmp`
3. Click **Deploy**.

---

## 🧪 Automated Test Suite

Run the complete test suite with pytest:

```bash
python -m pytest -v
```

Tests verify:
* ✅ End-to-end FastAPI ingestion and MoM synthesis routes
* ✅ Mu-law audio decoding and 16kHz resampling
* ✅ Pydantic schema validation for Gemini structured output
* ✅ ReportLab corporate PDF generator
* ✅ Calendar `.ics` attachment creation and email dispatch

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
