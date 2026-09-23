# PromptX Prelims

A real-time multiplayer game where players compete to generate AI images from prompts — without using forbidden words.

## Features

- 🎮 **Real-time Multiplayer** - Up to 70 players per game
- 🤖 **AI Image Generation** - HuggingFace FLUX.1-schnell integration
- 🚫 **Forbidden Words Challenge** - Smart validation system
- 🏆 **Live Leaderboard** - Real-time scoring and rankings
- ⚡ **WebSocket Sync** - Instant updates across all clients
- 🎯 **Multiple Difficulties** - Easy, Medium, Hard challenges
- 📊 **Host Dashboard** - Complete game control and monitoring

## Tech Stack

**Backend:**
- FastAPI (Python)
- PostgreSQL + SQLAlchemy
- Redis (session management)
- WebSocket (Socket.IO alternative)
- HuggingFace API

**Frontend:**
- React + TypeScript
- Vite
- TailwindCSS
- Framer Motion

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8001
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Deployment

See [Deployment Guide](./DEPLOYMENT.md) for Railway + Vercel deployment instructions.

## Environment Variables

**Backend (.env):**
```
AI_PROVIDER=huggingface
HF_TOKEN=your_huggingface_token
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

**Frontend (.env):**
```
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

## Game Flow

1. Host creates a game with custom settings
2. Players join using room code
3. Each round presents a target prompt + forbidden words
4. Players craft prompts to generate matching images
5. AI generates images (3 attempts per round)
6. Scoring based on accuracy and speed
7. Winner determined by total score across rounds

## License

MIT
