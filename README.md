# 🔐 VaultAlert — AI-Powered Smart Locker Security Platform

<div align="center">

![VaultAlert Banner](https://img.shields.io/badge/VaultAlert-Security%20Platform-6366f1?style=for-the-badge&logo=shield&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14.2-black?style=for-the-badge&logo=next.js&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-3C5280?style=for-the-badge&logo=eclipse-mosquitto&logoColor=white)

**Enterprise-grade IoT Security Platform with AI-powered threat intelligence, real-time surveillance, multi-factor biometric authentication, and live Telegram bot integration.**

[Demo](#) • [Documentation](#architecture) • [API Docs](http://localhost:8000/docs)

</div>

---

## ✨ Features

- 🤖 **AI Threat Intelligence** — Gemini Pro AI generates incident summaries and threat scores
- 📸 **Telegram Bot Integration** — Real-time security alerts with captured images streamed from your Telegram group directly to the dashboard
- 🔐 **Multi-Factor Authentication** — Fingerprint, Face Recognition, OTP, and Admin Override
- 📡 **Real-Time IoT Communication** — MQTT + WebSockets for live device telemetry and instant browser updates
- 🗂️ **Access Control Matrix** — Fine-grained permissions per locker per user (unlock, view live, manage)
- 📊 **Analytics Dashboard** — Recharts-powered trend graphs, KPI metrics, threat scoring
- 📹 **Live Camera Feed** — Per-locker surveillance viewer with tamper/motion overlay overlays
- 📄 **Report Export** — PDF incident reports, CSV access logs, audit trails
- 🔔 **Multi-Channel Notifications** — Push, SMS (Twilio), Email, Telegram, WhatsApp
- 🛡️ **Rate Limiting** — Redis-based sliding window protection (5/min auth, 60/min API)
- 🏢 **Multi-Organization** — Full tenant isolation for enterprise deployments

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion, Recharts |
| **Backend** | FastAPI (Python 3.12), SQLAlchemy (Async), Pydantic v2 |
| **Database** | PostgreSQL 16 + Alembic migrations |
| **Cache / Queue** | Redis 7 (rate limiting, OTP storage, PubSub) |
| **IoT Messaging** | MQTT via Eclipse Mosquitto broker |
| **Real-time** | WebSockets (FastAPI native) |
| **AI** | Google Gemini Pro API (with rule-based fallback) |
| **Storage** | AWS S3 (snapshot images, video clips) |
| **Auth** | JWT (access + refresh tokens), bcrypt password hashing |
| **Notifications** | SMTP Email, Twilio SMS, Telegram Bot API |
| **Containerization** | Docker + Docker Compose |

---

## 📁 Project Structure

```
VaultAlert/
├── backend/                    ← FastAPI Python Server
│   ├── app/
│   │   ├── api/v1/             ← REST API route handlers
│   │   │   ├── auth.py         ← Login, signup, OTP, refresh
│   │   │   ├── lockers.py      ← Locker CRUD + remote commands
│   │   │   ├── events.py       ← Security incidents
│   │   │   ├── analytics.py    ← Dashboard KPIs and charts
│   │   │   ├── users.py        ← Team management
│   │   │   ├── permissions.py  ← Access control matrix
│   │   │   ├── notifications.py← Notifications inbox
│   │   │   ├── devices.py      ← ESP32 device registration
│   │   │   ├── telegram.py     ← Telegram bot webhook
│   │   │   └── websockets.py   ← WS connections
│   │   ├── core/
│   │   │   ├── config.py       ← Environment settings
│   │   │   ├── database.py     ← Async PostgreSQL setup
│   │   │   ├── security.py     ← JWT + bcrypt
│   │   │   └── redis_client.py ← Redis connection pool
│   │   ├── models/models.py    ← SQLAlchemy ORM tables
│   │   ├── schemas/schemas.py  ← Pydantic request/response models
│   │   ├── services/
│   │   │   ├── ai_service.py   ← Gemini AI integration
│   │   │   ├── s3_service.py   ← AWS S3 uploads
│   │   │   └── notification_service.py
│   │   ├── workers/
│   │   │   ├── mqtt_worker.py  ← IoT device listener
│   │   │   ├── telegram_worker.py ← Telegram bot poller
│   │   │   ├── scheduler.py    ← Background APScheduler tasks
│   │   │   └── ws_manager.py   ← WebSocket room manager
│   │   └── main.py             ← App factory + router registration
│   ├── alembic/                ← Database migrations
│   └── requirements.txt
│
├── frontend/                   ← Next.js 14 React App
│   └── src/
│       ├── app/
│       │   ├── auth/           ← Login, Signup, Verify, Forgot Password
│       │   └── dashboard/      ← All protected dashboard pages
│       ├── components/
│       │   ├── layout/         ← Sidebar, Topbar
│       │   └── ui/             ← Modal, DataTable, Skeleton, EmptyState
│       ├── hooks/              ← useAuth, useLockers, useEvents, useSocket
│       ├── lib/
│       │   ├── api.ts          ← Axios HTTP client with JWT auto-refresh
│       │   └── utils.ts        ← Formatting helpers
│       └── types/index.ts      ← TypeScript interfaces
│
└── docker-compose.yml          ← All services orchestration
```

---

## 🚀 Getting Started

### Prerequisites
Make sure you have the following installed:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for database, Redis, MQTT)
- [Python 3.12+](https://www.python.org/downloads/)
- [Node.js 20+](https://nodejs.org/)
- [Git](https://git-scm.com/)

---

### 1. Clone the Repository

```bash
git clone https://github.com/tejaswinihatkar/VaultAlert.git
cd VaultAlert
```

---

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://vaultalert:vaultalert@localhost:5432/vaultalert

# Redis
REDIS_URL=redis://localhost:6379

# JWT Security
SECRET_KEY=your-super-secret-key-here-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# MQTT Broker
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# Telegram Integration
# Hardware Bot Token (used by hardware module to post)
TELEGRAM_HARDWARE_BOT_TOKEN=8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0

# Reader Bot Token (used by website backend to listen for alerts via Webhook)
TELEGRAM_BOT_TOKEN=8800613295:AAGe5LKW_5Hzig818_cvWztSximM8iQOXqI
TELEGRAM_CHAT_ID=-1004493857137

# AWS S3 (optional — uses mock if not configured)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
S3_BUCKET_NAME=vaultalert-media

# Google Gemini AI (optional — uses rule-based fallback if not configured)
GEMINI_API_KEY=

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
```

Also configure the frontend environment:

```bash
cd ../frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_WS_URL=ws://localhost:8000" >> .env.local
```

---

### 3. Start Infrastructure Services (Docker)

This starts PostgreSQL, Redis, and MQTT Mosquitto:

```bash
# From the project root
docker compose up -d postgres redis mosquitto
```

Or start ALL services at once (including backend + frontend):

```bash
docker compose up -d
```

---

### 4. Run the Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:
- **API:** `http://localhost:8000`
- **Swagger Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

### 5. Run the Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Start development server
npm run dev
```

Frontend will be available at: **`http://localhost:3000`**

---

## 📡 Telegram Bot Integration

> **Important — Telegram limitation.** A Telegram bot can **never** receive
> updates for messages posted by *another bot*, and can't `getFile` on another
> bot's uploads — **not even as group admin or with privacy disabled.** Admin
> rights only expose messages from *human* members. This is why alerts/images
> sent by the hardware bot never reached the dashboard.

### ✅ Recommended: API-Proxy ingestion (works around the bot-read limit)

Point the hardware at the backend **instead of** `api.telegram.org`. The backend
sees every upload first-hand (instant dashboard push over WebSocket) and then
forwards it on to the Telegram group. No Telegram bot-read restriction applies.

**The only change on the ESP32 / microcontroller** — swap the base URL:

| | Base URL |
|---|---|
| Before | `https://api.telegram.org` |
| After  | `https://vaultalert-api.onrender.com/api/v1/integrations/telegram` |

Keep the same path and payload, e.g.:

```
POST https://vaultalert-api.onrender.com/api/v1/integrations/telegram/bot<HARDWARE_BOT_TOKEN>/sendPhoto
     (multipart:  chat_id, caption, photo=@snapshot.jpg)
```

The proxy at `POST /integrations/telegram/bot{bot_token}/{method}` caches the
photo/alert, broadcasts it live, and transparently relays your request to
Telegram — so the group chat still receives the message exactly as before.

Alternatively, hardware can post **directly** (no Telegram round-trip) to:
- `POST /api/v1/camera/snapshot` — multipart JPEG
- `POST /api/v1/camera/snapshot-base64` — JSON base64 (low-spec boards)

### Legacy: Dual-Bot Reader webhook

A second **Reader Bot** in the group was the previous attempt, but Telegram's
bot-to-bot rule means it still cannot see the Hardware Bot's own posts — use the
API-Proxy path above instead. To (re)register a webhook if you still use it:

```bash
curl -X POST "https://vaultalert-api.onrender.com/api/v1/integrations/telegram/setup-webhook"
```

---

## 🔌 API Quick Reference

### Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin@123"}'

# Get current user profile
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Send Telegram Alert (Manual Test)
```bash
curl -X POST http://localhost:8000/api/v1/integrations/telegram/alert \
  -H "X-Telegram-Bot-Token: <YOUR_SECRET_KEY>" \
  -F "locker_id=<YOUR_LOCKER_UUID>" \
  -F "event_type=Tampering" \
  -F "description=Tamper detected on Vault casing!" \
  -F "severity=Critical" \
  -F "threat_score=0.90" \
  -F "photo=@/path/to/snapshot.jpg"
```

### List Security Events
```bash
curl -X GET "http://localhost:8000/api/v1/events?page=1&size=20" \
  -H "Authorization: Bearer <access_token>"
```

---

## 🏛️ Architecture Overview

```
                    ┌──────────────────┐
                    │  Telegram Group  │
                    │  (Vault Alerts)  │
                    └────────┬─────────┘
                             │ Poll / Webhook
                             ▼
┌──────────────┐    ┌────────────────────┐    ┌─────────────┐
│   ESP32 IoT  │───▶│   FastAPI Backend  │───▶│ PostgreSQL  │
│   Devices    │MQTT│  (Python 3.12)     │    │  Database   │
└──────────────┘    │                    │    └─────────────┘
                    │  ┌──────────────┐  │
                    │  │ MQTT Worker  │  │    ┌─────────────┐
                    │  │ TG Poller    │  │───▶│    Redis    │
                    │  │ Scheduler    │  │    │  (Cache)    │
                    │  │ WS Manager   │  │    └─────────────┘
                    │  └──────────────┘  │
                    └────────┬───────────┘
                             │ WebSocket
                             ▼
                    ┌────────────────────┐
                    │   Next.js 14 App   │
                    │   (localhost:3000) │
                    │                   │
                    │  Dashboard  Events │
                    │  Live Feed  Alerts │
                    └────────────────────┘
```

---

## 🔐 Default Credentials

After running the first-time database migration, you can create an admin account via:

```bash
# POST to signup endpoint
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@vaultalert.io",
    "password": "Admin@1234",
    "first_name": "VaultAlert",
    "last_name": "Admin",
    "role": "Admin"
  }'
```

---

## 🐳 Docker Compose Reference

```bash
# Start all services
docker compose up -d

# Check container status
docker compose ps

# View backend logs
docker compose logs -f backend

# Stop all services
docker compose down

# Reset database (WARNING: deletes all data)
docker compose down -v
```

---

## 📊 Dashboard Pages

| Route | Description |
|---|---|
| `/dashboard` | Main overview with KPIs, threat score, charts |
| `/dashboard/lockers` | Locker management + remote control |
| `/dashboard/live` | Live camera feed selector |
| `/dashboard/live/[id]` | Single locker live telemetry + camera |
| `/dashboard/events` | Security incidents with images |
| `/dashboard/alerts` | Notifications inbox |
| `/dashboard/access` | Access control permissions matrix |
| `/dashboard/users` | Team member management |
| `/dashboard/analytics` | Advanced charts and analytics |
| `/dashboard/reports` | PDF/CSV export center |
| `/dashboard/admin` | System health and admin controls |
| `/dashboard/settings` | Notification and sensitivity preferences |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📜 License

This project is proprietary software owned by the VaultAlert team. All rights reserved.

---

<div align="center">

**Built with ❤️ by the VaultAlert Engineering Team**

</div>
