# VaultAlert — Git Push Script
# Run this AFTER git is installed

$GIT = "C:\Program Files\Git\bin\git.exe"
$REPO_ROOT = "c:\Users\tejas\Downloads\Security\Security"

Set-Location $REPO_ROOT

Write-Host "==> Checking git version..." -ForegroundColor Cyan
& $GIT --version

Write-Host "`n==> Initializing git repository..." -ForegroundColor Cyan
& $GIT init

Write-Host "`n==> Configuring git user..." -ForegroundColor Cyan
& $GIT config user.email "tejaswinihatkar@gmail.com"
& $GIT config user.name "Tejaswini Hatkar"

Write-Host "`n==> Adding remote origin..." -ForegroundColor Cyan
& $GIT remote remove origin 2>$null
& $GIT remote add origin https://github.com/tejaswinihatkar/VaultAlert.git

Write-Host "`n==> Staging all files..." -ForegroundColor Cyan
& $GIT add .

Write-Host "`n==> Committing..." -ForegroundColor Cyan
& $GIT commit -m "feat: initial commit - VaultAlert AI Security Platform

- FastAPI backend with async PostgreSQL + Redis
- Next.js 14 frontend with Tailwind CSS + Framer Motion  
- Telegram bot integration for real-time security alerts
- MQTT worker for ESP32 IoT device telemetry
- WebSocket live dashboard updates
- Recharts analytics dashboard
- Multi-factor auth (Fingerprint/Face/OTP)
- Access control matrix with permissions
- PDF/CSV report export
- Docker Compose orchestration
- Alembic database migrations
- Comprehensive README with setup instructions"

Write-Host "`n==> Pushing to GitHub..." -ForegroundColor Cyan
& $GIT branch -M main
& $GIT push -u origin main --force

Write-Host "`n✅ Done! Check your repository at:" -ForegroundColor Green
Write-Host "   https://github.com/tejaswinihatkar/VaultAlert" -ForegroundColor Yellow
