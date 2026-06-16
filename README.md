# AI Video Generator

AI Video Generator is a production-grade, end-to-end automated system that transforms web articles, PDFs, or manual text inputs into highly engaging, completely original vertical (9:16) videos with AI-generated voiceovers, captions, transitions, and B-roll visuals.

The system is designed with a FastAPI backend (featuring Celery + Redis background processing) and a modern, glassmorphic Next.js (TypeScript + Tailwind CSS v4) frontend dashboard.

---

## Architecture Overview

```
                          ┌─────────────────────┐
                          │  Next.js Frontend   │
                          └──────────┬──────────┘
                                     │ (REST & WebSockets)
                                     ▼
                          ┌─────────────────────┐
                          │   FastAPI Backend   │
                          └──────────┬──────────┘
                                     │ (Queue Job)
                                     ▼
                          ┌─────────────────────┐
                          │    Redis Broker     │
                          └──────────┬──────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │  Celery Worker Process  │
                        └────────────┬────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │ M1: Ingestion │           │  M5: Script   │           │ M9: Visuals   │
 └───────┬───────┘           └───────┬───────┘           └───────┬───────┘
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │ M2: Whisper   │           │   M6: Voice   │           │ M10: AI Video │
 └───────┬───────┘           └───────┬───────┘           └───────┬───────┘
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │ M3: Extract   │           │   M7: Scene   │           │ M11: Assembly │
 └───────┬───────┘           └───────┬───────┘           └───────┬───────┘
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │   M4: Hooks   │           │  M8: Captions │           │  M12: Quality │
 └───────────────┘           └───────────────┘           └───────────────┘
```

---

## ⚡ Features

- **Multi-Source Ingestion**: Ingest data from webpage articles, PDF documents, or direct form entry.
- **AI-Powered Information Extraction**: Leverages Claude or GPT-4o to extract factual attributes while filtering out creator commentary.
- **Scroll-Stopping Hook Generator**: Evaluates 10 distinct hooks, scoring them dynamically to auto-select the strongest option.
- **Timed Script Generator**: Generates clean, conversational scripts suited for vertical video pacing (under 30 seconds).
- **Realistic Voiceovers**: Native integrations with ElevenLabs, Cartesia, and OpenAI TTS.
- **Styled Subtitles**: Auto-generates high-contrast ASS subtitles optimized for mobile viewport safety zones.
- **Parallel Visual Sourcing**: Crawls vertical/horizontal stock footage (Pexels) or creates clips using generative AI (Google Veo, Kling, Runway).
- **Automated Video Assembly**: Combines assets, adds transitions, overlaps background music, and burns in captions via FFmpeg.
- **Quality Engine & Self-Correction**: Scores the final video against four retention dimensions and triggers auto-regeneration if quality falls below threshold.
- **Robust Mock Engine**: Runs completely offline/local without API keys by leveraging simulated LLM patterns and FFmpeg background rendering.

---

## 🛠️ Prerequisites

Ensure you have the following installed on your system:
- **Python**: v3.10 or higher
- **Node.js**: v18 or higher (with npm)
- **Redis**: For running Celery tasks (local or Docker-based)
- **FFmpeg**: Required on your system path for video transcoding, keyframe extraction, audio normalization, and assembly.

---

## 🚀 Getting Started

### 1. Set Up Services (Redis)

Start Redis using Docker Compose:

```bash
docker compose up -d
```

### 2. Configure Environment Variables

Create `.env` files for both the backend and frontend using the root template:

```bash
# Copy template to backend
cp .env.example backend/.env

# Copy template to frontend
cp .env.example frontend/.env
```

Adjust the API keys in `backend/.env` for ElevenLabs, OpenAI, Anthropic, Pexels, or Runway. **If no API keys are provided, the system automatically runs in Mock mode using FFmpeg placeholder renderers and mock LLM pipelines.**

### 3. Backend Installation & Startup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

The REST API will be running at `http://localhost:8000`. You can view the API documentation at `http://localhost:8000/docs`.

### 4. Start Celery Task Worker

Open a new terminal window, activate your virtual environment, and run:

**On Linux/macOS:**
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

**On Windows:**
```bash
cd backend
celery -A app.workers.celery_app worker --pool=solo --loglevel=info
```

### 5. Frontend Installation & Startup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```

Open your browser and navigate to `http://localhost:3000`.

---

## 🧪 Verification & Testing

### Automated Backend Tests
Run pytest from the backend folder:
```bash
cd backend
python -m pytest
```

### End-to-End Manual Test
1. Access the dashboard at `http://localhost:3000`.
2. Click **Create Video** in the sidebar.
3. Select the input option (e.g., **Manual Entry**).
4. Input basic details or a text prompt.
5. Click **Generate Video**.
6. You will be redirected to the Generation Detail page. Watch the pipeline advance in real-time through WebSocket events:
   - *Extracting Info* ➔ *Creating Hooks* ➔ *Writing Script* ➔ *Generating Voice* ➔ *Assembling Video* ➔ *Completed!*
7. Play the generated video in the 9:16 vertical player.

---

## 📁 Repository Structure

```
├── backend/                           # FastAPI App
│   ├── app/
│   │   ├── api/                       # REST Endpoints & WebSockets
│   │   ├── db/                        # SQLite Session Manager
│   │   ├── models/                    # SQLModel Database Schemas
│   │   ├── pipeline/                  # Module 1 to 12 orchestration
│   │   ├── providers/                 # API Clients (Claude, OpenAI, Runway, etc.)
│   │   ├── services/                  # Job Service Layer
│   │   ├── utils/                     # FFmpeg, File, Validator helpers
│   │   └── workers/                   # Celery Config & Task definition
│   └── requirements.txt               # Backend dependencies
│
├── frontend/                          # Next.js App
│   ├── src/
│   │   ├── app/                       # Next.js pages (Dashboard, Create, Job Detail)
│   │   ├── hooks/                     # useJobWebSocket real-time hook
│   │   ├── lib/                       # API request client
│   │   └── types/                     # Shared TypeScript contracts
│   └── package.json                   # Frontend dependencies
│
├── docker-compose.yml                 # Redis container configuration
│   └── .env.example                   # Shared environment template
```
