# PromptX Prelims

**Multiplayer AI Image Prompt Competition Game**

Players compete by generating AI images from text prompts while being forbidden from using specific keywords. The team or individual who produces the most accurate image description — without using the obvious words — wins.

Supports up to **70 simultaneous players** per room with real-time WebSocket updates.

---

## Architecture

```
/
├── backend/        FastAPI + PostgreSQL + Redis + WebSockets
├── frontend/       React 18 + Vite + TypeScript + Tailwind CSS
├── shared/         Shared types (future use)
└── docker-compose.yml
```

---

## Quick Start (Docker — recommended)

### Prerequisites
- Docker Desktop installed and running

### Steps

```bash
# 1. Clone / open the project
cd "PromptX Prelims"

# 2. Create backend .env from example
copy backend\.env.example backend\.env

# 3. Start all services (Postgres, Redis, Backend, Frontend)
docker-compose up --build

# 4. Open the app
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/api/docs
```

The backend automatically runs migrations and seeds the 20 challenge database on first start.

---

## Manual Setup (without Docker)

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env — set DATABASE_URL, REDIS_URL, SECRET_KEY

# Run database migrations
alembic upgrade head

# Seed challenges
python -m app.challenges.seeder

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs at: **http://localhost:5173**
Backend API at:  **http://localhost:8000/api/docs**

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async URL | `postgresql+asyncpg://promptx:promptx@localhost:5432/promptx` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key (change in production!) | `change-me` |
| `AI_PROVIDER` | `mock` \| `openai` | `mock` |
| `IMAGE_GENERATION_API_KEY` | OpenAI / provider API key | _(blank for mock)_ |
| `IMAGE_EVALUATION_API_KEY` | Vision API key | _(blank for mock)_ |
| `MOCK_GENERATION_DELAY` | Simulated generation delay (seconds) | `2.0` |

---

## How to Play

### Host Flow

1. Go to **http://localhost:5173**
2. Click **Host a Contest** → Register/Login
3. Configure rounds, duration, player limit → **Create Room**
4. Share the **room code** with contestants
5. Click **START GAME** once players have joined
6. After each round, view scores → shortlist players → start next round

### Player Flow

1. Go to **http://localhost:5173**
2. Click **Join a Game**
3. Enter the room code and a display name
4. Click **Mark as Ready**
5. When the round starts:
   - Read the **Target** and **Forbidden Words**
   - Write a prompt in the editor (forbidden word detector highlights violations)
   - Click **GENERATE IMAGE**
   - Click your best image to set it as your final submission
6. View your score and leaderboard after the round

---

## Testing with Multiple Players (Browser Tabs)

1. Open Tab 1 → Host login → Create room → Share room code
2. Open Tabs 2-N → Join with different display names → Join same room code
3. Host clicks **START GAME**
4. All player tabs enter the game simultaneously
5. Each player writes prompts and generates images
6. After round ends, scores appear in all tabs

---

## AI Provider Configuration

### Mock Mode (default — no API key needed)
```
AI_PROVIDER=mock
```
Images come from picsum.photos (deterministic by prompt hash). Scores are simulated.

### OpenAI Mode (DALL-E 3 + GPT-4o Vision)
```
AI_PROVIDER=openai
IMAGE_GENERATION_API_KEY=sk-...
IMAGE_EVALUATION_API_KEY=sk-...
```

---

## Scoring System

| Component | Points | Basis |
|---|---|---|
| Image Accuracy | /50 | Vision model evaluates required objects, scene, relationships |
| Forbidden Word Compliance | /20 | 20 if no forbidden words, 0 if any detected |
| Creativity | /10 | Heuristic: how indirectly the prompt describes the target |
| Speed | /10 | How quickly a valid submission was made |
| Efficiency | /10 | Prompt length and vocabulary density |
| **Total** | **/100** | |

**Tie-breaking**: total score → accuracy → fastest submission → efficiency

---

## WebSocket Events

The client connects via:
```
ws://localhost:8000/ws/{ROOM_CODE}?token=<TOKEN>&is_host=0
```

Key server→client events:
- `lobby_state` — full lobby snapshot
- `round_started` — round begins with challenge data
- `timer_updated` — authoritative remaining seconds
- `image_generated` — image URL for a player's submission
- `score_calculated` — private score breakdown
- `leaderboard_updated` — public round standings
- `shortlist_announced` — who advances / is eliminated

---

## Project Structure

```
backend/
├── app/
│   ├── api/           REST routes (auth, games, players, rounds, challenges)
│   ├── challenges/    Challenge DB + 20 seed challenges
│   ├── config/        Settings (pydantic-settings) + structured logging
│   ├── database/      SQLAlchemy async engine + Redis helpers
│   ├── models/        SQLAlchemy ORM models
│   ├── schemas/       Pydantic request/response schemas
│   ├── scoring/       Scoring engine (5-component)
│   ├── services/      Business logic (rooms, rounds, prompts, auth, etc.)
│   ├── websockets/    WS connection manager + event emitter + handlers
│   └── workers/       Background tasks (image gen, scoring)
└── alembic/           Database migrations

frontend/
└── src/
    ├── components/    Shared, game, leaderboard, host UI components
    ├── hooks/         useGameWebSocket, useCountdown
    ├── pages/         Home, Join, Lobby, Game, Results, Host Dashboard
    ├── services/      WebSocket singleton, Axios API wrappers
    ├── stores/        Zustand (authStore, gameStore)
    └── types/         TypeScript domain types
```
