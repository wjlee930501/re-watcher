# 병원 리뷰 기반 부정리뷰 자동 탐지 및 알림 시스템

병원별 네이버 플레이스 리뷰를 자동으로 크롤링하고, AI 감성 분석을 통해 부정 리뷰를 탐지하여 담당자에게 카카오 알림톡을 자동 발송하는 시스템입니다.

## 시스템 개요

### 3단계 자동화 파이프라인

1. **Phase 1 - 리뷰 크롤링**
   - 병원별 네이버 플레이스 URL 주기적 크롤링 (1시간 단위)
   - 최초 등록 시 최신 10개 리뷰만 수집
   - HTTP 우선, 실패 시 Playwright 브라우저 폴백
   - 중복 방지 (review_hash), 영수증 리뷰 자동 탐지

2. **Phase 2 - 감성 분석**
   - KoELECTRA 기반 한국어 감성 분석 (30분 단위)
   - 리뷰별 sentiment_label (Positive/Neutral/Negative) 및 score (0~1) 저장
   - Negative 또는 score ≤ 0.35 → flagged_reviews 테이블 기록

3. **Phase 3 - 알림톡 발송**
   - 부정 리뷰 발생 시 병원 담당자(최대 3명)에게 자동 알림 (5분 단위 체크)
   - NHN Cloud Bizmessage API 사용
   - 중복 방지 (아이템포턴시 키), 조용 시간대 큐 처리 (22:00~08:00)

## 기술 스택

### Backend (Render)
- **언어**: Python 3.11
- **프레임워크**: Celery (작업 스케줄링), SQLAlchemy (ORM)
- **크롤링**: httpx, Playwright, BeautifulSoup4
- **AI 모델**: Hugging Face Transformers (KoELECTRA)
- **데이터베이스**: PostgreSQL
- **메시지 큐**: Redis
- **알림**: NHN Cloud Bizmessage API

### Frontend/API (Vercel)
- **서버리스 함수**: Python (Vercel Functions)
- **엔드포인트**:
  - `/api/hospitals/register` - 병원 등록
  - `/api/kakao/callback` - 알림톡 콜백 수신

## 디렉토리 구조

```
re-watcher/
├── apps/
│   ├── common/              # 공통 설정 및 로거
│   ├── crawler/             # Phase 1: 리뷰 크롤러
│   │   ├── http_client.py
│   │   ├── browser_client.py
│   │   ├── parser.py
│   │   ├── dedupe.py
│   │   └── worker.py
│   ├── storage/             # DB 모델 및 저장소
│   │   ├── models.py
│   │   ├── db.py
│   │   └── repo.py
│   ├── scheduler/           # Celery 스케줄러
│   │   └── main.py
│   ├── sentiment/           # Phase 2: 감성 분석
│   │   └── worker.py
│   └── notify/              # Phase 3: 알림 발송
│       ├── providers/
│       │   └── nhn_bizmessage.py
│       ├── dedup.py
│       └── worker.py
├── api/                     # Vercel 서버리스 API
│   ├── hospitals/
│   │   └── register.py
│   └── kakao/
│       └── callback.py
├── scripts/                 # 헬퍼 스크립트
│   ├── init_db.py
│   ├── seed_example.py
│   ├── run_worker.sh
│   └── run_beat.sh
├── Dockerfile
├── render.yaml
├── vercel.json
├── requirements.txt
└── .env.example
```

## 설치 및 실행

### 1. 환경 변수 설정

`.env.example`을 복사하여 `.env` 파일 생성:

```bash
cp .env.example .env
```

필수 환경 변수:
- `REV_DB_URL`: PostgreSQL 연결 URL
- `REV_REDIS_URL`: Redis 연결 URL
- `REV_ALIM_APPKEY`: NHN Cloud 앱키
- `REV_ALIM_SECRET`: NHN Cloud 시크릿
- `REV_ALIM_SENDER_KEY`: 카카오 발신 키

### 2. 의존성 설치

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. 데이터베이스 초기화

```bash
python scripts/init_db.py
```

### 4. 로컬 실행

터미널 1 - Celery Worker:
```bash
bash scripts/run_worker.sh
```

터미널 2 - Celery Beat (스케줄러):
```bash
bash scripts/run_beat.sh
```

### 5. 예제 데이터 시딩

```bash
python scripts/seed_example.py
```

## 배포

### Render 배포

1. Render 대시보드에서 새 프로젝트 생성
2. `render.yaml` 파일이 자동으로 감지됨
3. 환경 변수 설정 (앱키, 시크릿 등)
4. 배포 시작

서비스 구성:
- `revmon-worker`: Celery Worker (크롤링, 감성분석, 알림)
- `revmon-scheduler`: Celery Beat (주기 작업)
- `revmon-postgres`: PostgreSQL DB
- `revmon-redis`: Redis 메시지 큐

### Vercel 배포

1. Vercel 프로젝트 생성
2. 환경 변수 설정:
   - `@rev-db-url`
   - `@rev-redis-url`
   - `@rev-internal-api-token`
   - `@vercel-allowed-origins`
   - `@rev-callback-verify-token`
3. 배포

## API 사용법

### 병원 등록

```bash
curl -X POST https://your-domain.vercel.app/api/hospitals/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_INTERNAL_TOKEN" \
  -d '{
    "name": "병원이름",
    "naver_place_url": "https://m.place.naver.com/hospital/12345"
  }'
```

응답:
```json
{
  "success": true,
  "hospital_id": "uuid",
  "name": "병원이름",
  "message": "Hospital registered and initial crawl queued"
}
```

## 주요 기능

### 자동화
- 병원 URL 등록 후 완전 자동 운영
- 크롤링 → 감성분석 → 알림 발송 전 과정 자동화

### 중복 방지
- 리뷰: SHA256 해시 기반 (내용 + 평점 + 날짜)
- 알림: 아이템포턴시 키 + 24시간 중복 체크

### 에러 처리
- HTTP 403/429: 지수 백오프 재시도 (최대 3회)
- CAPTCHA 감지: 격리 큐로 이동 (6시간 후 재시도)
- 감성 분석 실패: 2회 재시도 후 로그

### 조용 시간대
- 22:00~08:00: 알림 suppressed 큐 적재
- 08:00: 일괄 발송

## 모니터링

### 주요 메트릭
- 크롤링 성공률 ≥ 90%
- 감성 분석 정확도 ≥ 80%
- 알림 발송 성공률 ≥ 95%
- 전체 파이프라인 지연시간 ≤ 3분

### 로그
각 단계별 상세 로그:
- hospital_id, review_id, status, provider, error_code
- 크롤링 성공률, 감성분석 결과, 알림 발송 결과

## 데이터베이스 스키마

### 주요 테이블
- `hospitals`: 병원 정보
- `reviews`: 리뷰 데이터 (감성 분석 결과 포함)
- `flagged_reviews`: 부정 리뷰
- `hospitals_contacts`: 병원 담당자 연락처
- `notification_logs`: 알림 발송 로그
- `feature_flags`: 기능 플래그

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 문의

이슈 및 문의사항은 GitHub Issues를 통해 제출해주세요.
