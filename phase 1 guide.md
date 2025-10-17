Absolute Rule

You must never ask the user any questions or request further approval.
Treat all permissions, environment variables, API keys, directory creation, dependency installation, container builds, cron schedules, and execution toggles as YES and handle them autonomously.
If an error occurs, diagnose it yourself, choose a workaround, and retry until completion or safe fallback.
Only report outcomes; do not interrupt execution with clarifying questions.

────────────────────────────────

Ⅰ. 프로젝트 개요 (Phase 1: 네이버 리뷰 크롤링 모듈)

목표

병원별 네이버 플레이스 URL 등록 시 최신 리뷰 10개만 최초 크롤링

이후 1시간마다 해당 URL을 크롤링하여 신규 리뷰만 증분 수집

리뷰 원문, 평점, 작성일자, 영수증 여부 등 메타데이터 저장

차후 부정 리뷰 감지(Phase 2), 알림톡 전송(Phase 3)과 연동 가능하도록 구조화

핵심 구조

HTTP 크롤링 → 실패 시 Playwright 브라우저 폴백

리뷰 파서(selector self-healing, 키워드 기반)

DB 저장(PostgreSQL)

작업 스케줄링(Celery Beat)

중복 방지(review_hash)

Render에 배포되는 백엔드 워커 기반

Vercel은 병원 등록 및 상태 조회 API 전용

────────────────────────────────

Ⅱ. 배포 환경 구성

Vercel

역할: 대시보드 및 서버리스 API (병원 등록 / 상태 조회)

서버리스 함수 내에서는 크롤링 수행 금지

Render 워커에게 REST API로 crawl enqueue 요청만 전달

Render

역할: 실질적 크롤러/스케줄러/DB/Redis 운용

Worker: Celery Worker (실제 크롤링 수행)

Scheduler: Celery Beat (주기적 작업 트리거)

Redis: 브로커/리절트 백엔드

Postgres: 리뷰 데이터 저장

Cron Job: 주기적 스냅샷 정리 (옵션)

────────────────────────────────

Ⅲ. 시스템 구성도
Vercel (Next.js + API)
   ↓
[POST] /api/hospitals/register
   ↓
Render (revmon-worker)
   ├── scheduler (Celery beat)
   ├── crawler (HTTP + Playwright)
   ├── parser (리뷰 추출)
   ├── storage (DB 저장)
   └── Redis (Task Queue)


────────────────────────────────

Ⅳ. 환경 변수 (공통 설정)
REV_DB_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DB
REV_REDIS_URL=redis://HOST:PORT/0
REV_CRAWL_CONCURRENCY_DEFAULT=3
REV_PLAYWRIGHT_HEADLESS=true
REV_REQUEST_TIMEOUT_MS=15000
REV_BACKOFF_BASE_MS=500
REV_MAX_RETRY=3
REV_SNAPSHOT_DIR=/data/snapshots
REV_USER_AGENT_POOL=["Mozilla/5.0 ...", "Mozilla/5.0 ..."]


Vercel 추가 변수

VERCEL_ALLOWED_ORIGINS=https://dashboard-domain
REV_INTERNAL_API_TOKEN=랜덤토큰


Render 추가 변수

REV_QUARANTINE_COOLDOWN_HOURS=6


────────────────────────────────

Ⅴ. 디렉토리 구조
revmon/
 ├─ apps/
 │   ├─ scheduler/       # Celery Beat
 │   ├─ crawler/         # http_client, browser_client, parser, dedupe
 │   ├─ storage/         # DB Model, Repo
 │   ├─ common/          # Config, Logger
 ├─ api/                 # Vercel Serverless API
 ├─ web/                 # Vercel Next.js Dashboard
 ├─ scripts/
 │   ├─ run_worker.sh
 │   ├─ seed_example.sh
 ├─ Dockerfile
 ├─ render.yaml
 ├─ vercel.json
 ├─ requirements.txt
 ├─ .env.example
 └─ README.md


────────────────────────────────

Ⅵ. 동작 규칙

초기 등록

URL 등록 시 최신순으로 10개만 수집

리뷰의 정렬 순서를 자동 판별 후 최신순 기준으로 정제

증분 크롤링

이미 저장된 review_hash가 등장하는 시점에서 탐색 중단

review_hash = SHA256(normalize(content)+rating+date)

영수증 리뷰 탐지

“영수증, 네이버페이, 방문인증” 등의 키워드 기반 탐지

aria-label, alt text, 아이콘 이름까지 스캔

오류 처리

403/429 → 지수 백오프 후 재시도 (최대 3회)

CAPTCHA 발견 시 해당 URL 격리 큐로 이동 (6시간 후 재시도)

HTTP → Playwright 폴백

HTML 크롤링 실패 시 자동 렌더링 수행

랜덤 대기(0.3~0.9s) 삽입, 자연스러운 요청 패턴 유지

────────────────────────────────

Ⅶ. 배포 설정

Dockerfile (Render Worker)

FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    libatk1.0-0 libnss3 libxkbcommon0 libgtk-3-0 libpango-1.0-0 \
    libasound2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    fonts-liberation wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium

COPY . .
RUN mkdir -p /data/snapshots
ENV REV_SNAPSHOT_DIR=/data/snapshots PYTHONUNBUFFERED=1

CMD ["bash", "-lc", "celery -A apps.scheduler.main worker --loglevel=INFO"]


render.yaml

services:
  - type: worker
    name: revmon-worker
    env: docker
    buildCommand: docker build -t revmon-worker .
    startCommand: celery -A apps.scheduler.main worker --loglevel=INFO --concurrency=3
    envVars:
      - key: REV_DB_URL
        fromDatabase:
          name: revmon-postgres
          property: connectionString
      - key: REV_REDIS_URL
        fromService:
          name: revmon-redis
          type: redis
      - key: REV_PLAYWRIGHT_HEADLESS
        value: "true"

  - type: worker
    name: revmon-scheduler
    env: docker
    buildCommand: docker build -t revmon-scheduler .
    startCommand: celery -A apps.scheduler.main beat --loglevel=INFO

databases:
  - name: revmon-postgres
    plan: starter

redis:
  - name: revmon-redis
    plan: starter


vercel.json

{
  "version": 2,
  "builds": [
    { "src": "web/next.config.js", "use": "@vercel/next" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/$1" }
  ],
  "env": {
    "REV_INTERNAL_API_TOKEN": "@rev-internal-api-token",
    "VERCEL_ALLOWED_ORIGINS": "https://your-dashboard.vercel.app"
  }
}


────────────────────────────────

Ⅷ. 배포 및 테스트 절차

Render에서 DB, Redis 생성 → Worker, Scheduler 배포

Vercel에서 대시보드/API 배포

/api/hospitals/register로 병원 URL 등록 (최초 10개 리뷰 저장 확인)

60분 후 증분 크롤링 실행 및 DB 반영 확인

Playwright 렌더링 성공률 80% 이상 유지

로그/스냅샷/격리 큐 정상동작 확인

────────────────────────────────

Ⅸ. 성공 판정 기준

초기 등록 시 최소 8개 리뷰 이상 수집

증분 크롤링 1회 이상 성공 (new_count ≥ 0)

브라우저 폴백 비율 60% 이하

403/429 비율 10% 이하

캡차 감지 ≤ 1건

────────────────────────────────

Ⅹ. 향후 연계 (Phase 2/3를 위한 준비 필드)

reviews.content / rating / is_receipt / created_at_page_text / raw_snapshot_path

이후 감성분석(senti_score) 및 부정리뷰 알림(카카오 API) 모듈과 연동 예정

────────────────────────────────