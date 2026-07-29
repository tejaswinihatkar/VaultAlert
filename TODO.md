# VaultAlert — TODO & Implementation Roadmap

> **Current Status:** Phase 1–4 complete. Backend core, real-time layer, and dashboard frontend are done.
> This document tracks everything remaining to reach a fully production-ready system.

---

## 🚀 How to Run the Project

### Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Docker Desktop | Latest | https://docker.com/products/docker-desktop |
| Node.js | 20+ | https://nodejs.org |
| Python | 3.12+ | https://python.org |
| Git | Any | https://git-scm.com |

---

### Step 1 — Set Up Environment

```bash
cd "c:\Users\A\Desktop\Security"

# Copy environment file and fill in values
copy .env.example .env
```

Open `.env` and set **at minimum**:
```env
SECRET_KEY=your-random-64-character-secret-key-here
POSTGRES_PASSWORD=your-secure-password
REDIS_PASSWORD=your-redis-password
```

---

### Step 2 — Start All Services with Docker

```bash
# Start everything
docker compose --profile dev up -d

# Check container health
docker compose ps

# Watch backend logs
docker compose logs -f backend
```

**Services available after startup:**

| Service | URL | Notes |
|---------|-----|-------|
| 🌐 Web Dashboard | http://localhost:3000 | Next.js frontend |
| 📖 API Swagger Docs | http://localhost:8000/docs | FastAPI auto-docs |
| 🗄️ PgAdmin | http://localhost:5050 | admin@vaultalert.io / PgAdminVault_2024 |
| ⚡ MQTT Broker | mqtt://localhost:1883 | Mosquitto |
| 💾 Redis | redis://localhost:6379 | Cache + pub/sub |

---

### Step 3 — Run Frontend Locally (No Docker)

```bash
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Start dev server (hot reload)
npm run dev

# Open: http://localhost:3000
```

---

### Step 4 — Run Backend Locally (No Docker)

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Start only DB/Redis/MQTT via Docker
docker compose up postgres redis mosquitto -d

# Run FastAPI with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API Docs: http://localhost:8000/docs
```

---

### Step 5 — Run IoT Simulator (No Hardware Needed)

```bash
# Install simulator deps
pip install aiomqtt loguru

# Create an org + locker via API first (http://localhost:8000/docs)
# Then run simulator with the UUIDs:

python iot/simulator.py \
  --lockers <locker-uuid> \
  --org <org-uuid> \
  --telemetry-interval 5 \
  --event-interval 15
```

---

### Step 6 — Preview Only (Static HTML, No Backend)

```bash
# Option A: Open directly
start "" "c:\Users\A\Desktop\Security\preview.html"

# Option B: Serve via Python HTTP server
python -m http.server 7890 --directory "c:\Users\A\Desktop\Security"
# Open: http://localhost:7890/preview.html
```

---

### Stop / Reset

```bash
docker compose down          # Stop (keeps data)
docker compose down -v       # Stop + wipe all volumes
```

---

## ✅ Already Completed

- [x] Docker Compose (PostgreSQL, Redis, Mosquitto, Nginx, PgAdmin)
- [x] Nginx reverse proxy with rate limiting, WS upgrade, security headers
- [x] Environment variables template (.env.example)
- [x] FastAPI application with lifespan (startup/shutdown hooks)
- [x] 13 SQLAlchemy database models with enums and relationships
- [x] Pydantic schemas for all API request/response types
- [x] Generic typed Repository Pattern (base, user, locker, event repos)
- [x] Auth Service — signup, login, OTP, JWT rotation, logout
- [x] AES-256-GCM biometric template encryption
- [x] JWT + bcrypt security utilities
- [x] RBAC dependency guards (7 role levels)
- [x] Auth REST API — /signup /login /refresh /logout /verify-otp /me
- [x] Locker REST API — CRUD + remote unlock/lock/lockdown
- [x] Analytics REST API — dashboard KPIs, access trend, threat trend
- [x] MQTT subscriber daemon (auto-reconnect, parses telemetry/events/status)
- [x] WebSocket manager (org-scoped + locker-scoped rooms)
- [x] WebSocket endpoints with JWT auth + ping/pong keepalive
- [x] Redis pub/sub device command routing
- [x] Notification service (Email/SMTP, SMS/Twilio, Push/FCM)
- [x] IoT device simulator (iot/simulator.py)
- [x] Next.js 14 + TailwindCSS dark glassmorphic design system
- [x] Axios API client with silent JWT auto-refresh on 401
- [x] WebSocket hooks (org + locker rooms, auto-reconnect)
- [x] Login page (Zod validation, JWT storage)
- [x] Sidebar + Topbar layout components
- [x] Dashboard page (KPI cards, area chart, event feed, locker grid, threat banner)
- [x] Live Locker page (camera, telemetry gauges, remote controls, real-time WS)
- [x] Interactive HTML preview (preview.html)
- [x] README with full documentation

---

## 📋 TODO — Remaining Implementation

---

### 🔴 HIGH PRIORITY — Backend APIs

- [ ] **Alembic setup**
  ```bash
  cd backend
  alembic init alembic
  # edit alembic/env.py for async support
  alembic revision --autogenerate -m "initial_schema"
  alembic upgrade head
  ```

- [ ] **Events API** — `app/api/v1/events.py`
  - `GET /api/v1/lockers/{id}/events` — paginated event list with filters
  - `POST /api/v1/events/{id}/resolve` — mark event resolved

- [ ] **Access Logs API** — `app/api/v1/access_logs.py`
  - `GET /api/v1/lockers/{id}/access-logs` — paginated access history

- [ ] **Device Registration API** — `app/api/v1/devices.py`
  - `POST /api/v1/devices` — register ESP32 to locker
  - `GET /api/v1/devices/{id}` — device detail + last ping
  - `POST /api/v1/devices/{id}/firmware-update` — trigger OTA

- [ ] **Organization API** — `app/api/v1/organizations.py`
  - `POST /api/v1/organizations` — create org (Admin only)
  - `GET /api/v1/organizations/{id}` — org detail
  - `PUT /api/v1/organizations/{id}` — update settings

- [ ] **User Management API** — `app/api/v1/users.py`
  - `GET /api/v1/users` — list org users
  - `PUT /api/v1/users/{id}` — update profile / role
  - `DELETE /api/v1/users/{id}` — deactivate account

- [ ] **Permission API** — `app/api/v1/permissions.py`
  - `POST /api/v1/permissions` — grant locker access to user
  - `GET /api/v1/lockers/{id}/permissions` — list who has access
  - `DELETE /api/v1/permissions/{id}` — revoke access
  - Support `valid_from` / `valid_until` for temporary access

- [ ] **Notification API** — `app/api/v1/notifications.py`
  - `GET /api/v1/notifications` — inbox with unread count
  - `PUT /api/v1/notifications/{id}/read` — mark read
  - `PUT /api/v1/notifications/read-all` — clear all

- [ ] **Locker Settings API**
  - `GET /api/v1/lockers/{id}/settings`
  - `PUT /api/v1/lockers/{id}/settings`

- [ ] **Fingerprint & Face Enrollment API**
  - `POST /api/v1/fingerprints` — store encrypted template
  - `DELETE /api/v1/fingerprints/{id}` — remove slot
  - `POST /api/v1/faces` — store encrypted face encoding
  - `DELETE /api/v1/faces/{id}` — remove face

- [ ] **Reports API** — `app/api/v1/reports.py`
  - `GET /api/v1/reports/incident` → PDF download
  - `GET /api/v1/reports/access-logs` → CSV/Excel download
  - `GET /api/v1/reports/audit` → admin audit trail

- [ ] **AI Service** — `app/services/ai_service.py`
  - Gemini API integration for natural language incident summaries
  - Natural language event search endpoint
  - Anomaly scoring from repeated access pattern analysis

- [ ] **S3 Upload Service** — `app/services/s3_service.py`
  - Upload snapshot on every security event
  - Generate pre-signed URLs for frontend media display
  - Lifecycle policy enforcement (delete after retention days)

- [ ] **Background Scheduler** — `app/workers/scheduler.py`
  - Check battery < threshold every 15 min → notify
  - Mark devices offline if no heartbeat > 5 min
  - Daily security summary email
  - Clean expired OTPs from Redis

- [ ] **Audit Log Middleware** — `app/middleware/audit.py`
  - Auto-log all POST/PUT/DELETE with user, IP, resource

- [ ] **Rate Limiting** — `app/middleware/rate_limit.py`
  - Auth: 5 req/min per IP
  - General API: 60 req/min per user

---

### 🔴 HIGH PRIORITY — Frontend Pages

- [ ] **Locker Management** — `/dashboard/lockers`
  - Sortable/filterable data table
  - Create locker modal (name, location, GPS coords)
  - Edit locker drawer
  - Delete confirmation dialog
  - Assign owner dropdown

- [ ] **Events & Surveillance** — `/dashboard/events`
  - Timeline view with severity filter
  - Date range picker
  - Before/after snapshot viewer
  - AI incident summary display
  - Resolve event button

- [ ] **Access Control** — `/dashboard/access`
  - User permission matrix table
  - Grant access modal (user + locker + time range)
  - Temporary access with expiry date/time picker
  - Revoke access with confirmation

- [ ] **Users** — `/dashboard/users`
  - User table (role, status, last login)
  - Invite user by email + role
  - Change role dropdown
  - Deactivate toggle

- [ ] **Alerts** — `/dashboard/alerts`
  - Notification inbox
  - Mark read / clear all
  - Filter by severity (Critical / Warning / Info)

- [ ] **Analytics** — `/dashboard/analytics`
  - Full access trend chart (30/60/90 days)
  - Threat trend chart
  - Peak hours heatmap
  - Most accessed locker chart
  - Fingerprint success rate donut

- [ ] **Reports** — `/dashboard/reports`
  - Report type selector
  - Date range input
  - Export PDF / CSV / Excel buttons

- [ ] **Admin Panel** — `/dashboard/admin`
  - Organization management
  - Firmware release management
  - System health overview

- [ ] **Settings** — `/dashboard/settings`
  - Notification preferences per channel
  - Video retention days
  - Motion sensitivity
  - Auto-lock timer

- [ ] **Auth — Signup** — `/auth/signup`
- [ ] **Auth — OTP Verify** — `/auth/verify`
- [ ] **Auth — Forgot Password** — `/auth/forgot-password`
- [ ] **Route guard middleware** — `src/middleware.ts`

---

### 🟡 MEDIUM PRIORITY

- [ ] **Frontend TypeScript types** — `src/types/index.ts`
- [ ] **React Query hooks** — `useLockers`, `useEvents`, `useNotifications`, `useAuth`
- [ ] **Reusable UI components** — `Modal`, `DataTable`, `DateRangePicker`, `EmptyState`, `Skeleton`
- [ ] **Error boundaries** with friendly fallback UI
- [ ] **Mobile-responsive layout** — sidebar collapses to bottom nav
- [ ] **Loading skeletons** for all data tables and cards
- [ ] **Firebase Admin initialization** — `app/core/firebase.py`
- [ ] **Email Jinja2 templates** — welcome, alert, OTP, report
- [ ] **Pytest test suite** — auth, lockers, analytics (with async fixtures)

---

### 🟢 LOWER PRIORITY — Future Roadmap

#### Flutter Mobile App — `mobile/`
- [ ] Project scaffold (`flutter create mobile`)
- [ ] Auth screens (login, OTP, biometric via `local_auth`)
- [ ] Dashboard screen (KPI tiles, event list)
- [ ] Live camera screen (RTSP/WebRTC player)
- [ ] Push notifications (Firebase Cloud Messaging)
- [ ] Timeline / history screen
- [ ] Settings screen

#### ESP32 Firmware — `iot/esp32_firmware/`
- [ ] PlatformIO project setup (`platformio.ini`)
- [ ] MQTT connection with auto-reconnect
- [ ] Fingerprint sensor read loop (AS608/R307)
- [ ] Door sensor + tamper switch interrupt handlers
- [ ] Solenoid lock GPIO control
- [ ] Buzzer alert patterns (success/fail/tamper)
- [ ] OTA firmware update receiver

#### DevOps / Cloud
- [ ] GitHub Actions CI — pytest on every push
- [ ] GitHub Actions CD — Docker build + push to ECR on tag
- [ ] AWS deployment guide (EC2, RDS, ElastiCache, S3, CloudFront)
- [ ] Kubernetes Helm chart
- [ ] Prometheus + Grafana monitoring dashboards
- [ ] Let's Encrypt SSL auto-renewal

---

## 📁 Files Still To Create

```
backend/
  alembic.ini
  alembic/env.py
  alembic/versions/001_initial_schema.py
  app/api/v1/events.py
  app/api/v1/users.py
  app/api/v1/organizations.py
  app/api/v1/permissions.py
  app/api/v1/notifications.py
  app/api/v1/devices.py
  app/api/v1/reports.py
  app/api/v1/fingerprints.py
  app/services/ai_service.py
  app/services/s3_service.py
  app/services/firmware_service.py
  app/services/report_service.py
  app/workers/scheduler.py
  app/middleware/audit.py
  app/middleware/rate_limit.py
  app/templates/email/welcome.html
  app/templates/email/alert.html
  app/templates/email/otp.html
  tests/conftest.py
  tests/test_auth.py
  tests/test_lockers.py
  tests/test_analytics.py

frontend/src/
  app/auth/signup/page.tsx
  app/auth/verify/page.tsx
  app/auth/forgot-password/page.tsx
  app/dashboard/lockers/page.tsx
  app/dashboard/events/page.tsx
  app/dashboard/access/page.tsx
  app/dashboard/users/page.tsx
  app/dashboard/alerts/page.tsx
  app/dashboard/analytics/page.tsx
  app/dashboard/reports/page.tsx
  app/dashboard/admin/page.tsx
  app/dashboard/settings/page.tsx
  components/ui/Modal.tsx
  components/ui/DataTable.tsx
  components/ui/EmptyState.tsx
  components/ui/Skeleton.tsx
  hooks/useLockers.ts
  hooks/useEvents.ts
  hooks/useNotifications.ts
  hooks/useAuth.ts
  types/index.ts
  middleware.ts

mobile/ (entire Flutter app)
iot/esp32_firmware/ (PlatformIO source)
.github/workflows/ci.yml
.github/workflows/deploy.yml
```

---

## 🔑 Quick Reference Commands

```bash
# ── Start everything ──────────────────────────────────────────────
docker compose --profile dev up -d

# ── Rebuild after changes ─────────────────────────────────────────
docker compose --profile dev up -d --build

# ── View logs ─────────────────────────────────────────────────────
docker compose logs -f backend
docker compose logs -f frontend

# ── Run DB migrations ─────────────────────────────────────────────
docker compose exec backend alembic upgrade head

# ── Open database shell ───────────────────────────────────────────
docker compose exec postgres psql -U vaultalert_admin -d vaultalert

# ── Open Redis shell ──────────────────────────────────────────────
docker compose exec redis redis-cli -a <your-redis-password>

# ── Run backend tests ─────────────────────────────────────────────
docker compose exec backend pytest tests/ -v --asyncio-mode=auto

# ── IoT simulator ─────────────────────────────────────────────────
python iot/simulator.py --lockers <uuid> --org <uuid> --event-interval 10

# ── Stop containers (keep data) ───────────────────────────────────
docker compose down

# ── Full reset (wipes all DB data) ───────────────────────────────
docker compose down -v
```

---

## 🌐 Key URLs

| Resource | URL |
|----------|-----|
| Static Preview | `c:\Users\A\Desktop\Security\preview.html` |
| Preview Server | http://localhost:7890/preview.html |
| Web App | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| API ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |
| PgAdmin | http://localhost:5050 |

---

*VaultAlert v1.0.0 — Last updated: 2026-07-16*
