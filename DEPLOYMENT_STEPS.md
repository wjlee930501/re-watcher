# 배포 단계별 가이드

## ✅ 완료된 단계

- [x] GitHub 저장소 생성 및 코드 푸시
  - Repository: https://github.com/wjlee930501/re-watcher

---

## 📋 Render 배포 (백엔드 Worker)

### 1. PostgreSQL 생성

1. [Render Dashboard](https://dashboard.render.com) → "New +" → "PostgreSQL"
2. 설정:
   ```
   Name: revmon-postgres
   Database: revmon
   User: revmon
   Region: Singapore (또는 가장 가까운 리전)
   Plan: Starter ($7/월)
   ```
3. "Create Database" 클릭
4. **Internal Database URL 복사** (예: `postgresql://revmon:...@...render.com/revmon`)

### 2. Redis 생성

1. "New +" → "Redis"
2. 설정:
   ```
   Name: revmon-redis
   Region: Singapore (PostgreSQL과 동일)
   Plan: Starter ($7/월)
   Max Memory Policy: allkeys-lru
   ```
3. "Create Redis" 클릭
4. **Internal Redis URL 복사** (예: `redis://...render.com:6379`)

### 3. Blueprint 배포

1. "New +" → "Blueprint"
2. "Connect a repository" → `wjlee930501/re-watcher` 선택
3. Render가 `render.yaml` 자동 감지
4. "Apply" 클릭
5. 2개 서비스 생성 확인:
   - `revmon-worker`
   - `revmon-scheduler`

### 4. 환경 변수 설정

**Worker 서비스** 대시보드 → "Environment" 탭:

```bash
# NHN Cloud 설정 (필수)
REV_ALIM_PROVIDER=nhn_bizmessage
REV_ALIM_APPKEY=<NHN Cloud에서 발급받은 앱키>
REV_ALIM_SECRET=<NHN Cloud에서 발급받은 시크릿>
REV_ALIM_SENDER_KEY=<카카오 발신 키>

# 템플릿 코드 (선택, 기본값 사용 가능)
REV_ALIM_TEMPLATE_CODE=RV_NEG_REVIEW_ALERT_01

# 콜백 검증 토큰 (Vercel과 동일하게 설정)
REV_CALLBACK_VERIFY_TOKEN=<랜덤 생성한 토큰>
```

**토큰 생성 방법:**
```bash
# PowerShell에서
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})

# 또는 Python에서
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Scheduler 서비스**도 동일한 환경 변수 설정

### 5. 데이터베이스 초기화

Worker 서비스 → "Shell" 탭:
```bash
python scripts/init_db.py
```

성공 메시지 확인:
```
✅ All tables created successfully!
```

### 6. 서비스 시작 확인

- Worker 로그에서 "celery@... ready" 확인
- Scheduler 로그에서 "beat: Starting..." 확인

---

## 📋 Vercel 배포 (API 엔드포인트)

### 1. Vercel 로그인

로컬 터미널에서:
```bash
vercel login
```

### 2. 프로젝트 연결

```bash
cd c:\Users\a\Documents\projects\re-watcher
vercel
```

질문에 답변:
- Set up and deploy?: **Y**
- Which scope?: (계정 선택)
- Link to existing project?: **N**
- Project name: **re-watcher**
- Directory: **./** (엔터)
- Modify settings?: **N**

### 3. 환경 변수 설정

Render에서 복사한 URL들을 사용:

```bash
# PostgreSQL URL
vercel env add REV_DB_URL production
# 붙여넣기: postgresql://revmon:...@...render.com/revmon

# Redis URL
vercel env add REV_REDIS_URL production
# 붙여넣기: redis://...render.com:6379

# 내부 API 토큰 (새로 생성)
vercel env add REV_INTERNAL_API_TOKEN production
# 붙여넣기: 랜덤 생성한 토큰

# CORS 허용 도메인
vercel env add VERCEL_ALLOWED_ORIGINS production
# 붙여넣기: https://your-dashboard-domain.vercel.app

# 콜백 검증 토큰 (Render와 동일)
vercel env add REV_CALLBACK_VERIFY_TOKEN production
# 붙여넣기: Render에서 사용한 동일한 토큰
```

### 4. 프로덕션 배포

```bash
vercel --prod
```

배포 URL 확인:
```
https://re-watcher.vercel.app
```

---

## 🧪 통합 테스트

### 1. 병원 등록 테스트

```bash
curl -X POST https://re-watcher.vercel.app/api/hospitals/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <REV_INTERNAL_API_TOKEN>" \
  -d '{
    "name": "테스트병원",
    "naver_place_url": "https://m.place.naver.com/hospital/example",
    "alert_phone": "+821012345678"
  }'
```

예상 응답:
```json
{
  "hospital_id": "abc123",
  "message": "Hospital registered. Initial crawl task queued."
}
```

### 2. Render Worker 로그 확인

1. Worker 대시보드 → "Logs" 탭
2. 크롤링 시작 로그 확인:
   ```
   Starting initial crawl for hospital_id=abc123
   Fetched 10 reviews for hospital abc123
   ```

### 3. 30분 후 감성 분석 확인

Scheduler 로그에서:
```
Running sentiment analysis...
Analyzed 10 reviews, flagged 2 negative reviews
```

### 4. 알림 발송 확인

Worker 로그에서:
```
Sending notification for flagged review...
Notification sent successfully
```

등록한 전화번호로 카카오톡 알림 수신 확인

---

## 📊 모니터링

### Render 대시보드

- **Worker**
  - CPU/메모리 사용률
  - 로그에서 에러 확인
  - 작업 처리 시간

- **Scheduler**
  - Beat 스케줄 실행 확인
  - 주기적 작업 로그

- **PostgreSQL**
  - 연결 수
  - 쿼리 성능
  - 스토리지 사용량

- **Redis**
  - 메모리 사용량
  - 키 개수
  - 명령 처리 속도

### Vercel 대시보드

- **Functions**
  - 실행 시간
  - 에러율
  - 호출 횟수

---

## ⚠️ 주의사항

### NHN Cloud 알림톡 템플릿

템플릿 등록 및 승인 필요:
```
템플릿 코드: RV_NEG_REVIEW_ALERT_01

내용:
[#{hospitalName}] 부정 리뷰 알림

#{reviewSnippet}

👉 전체 보기: #{reviewLink}

💡 #{howToRespond}
```

치환 변수:
- `hospitalName`: 병원명
- `reviewSnippet`: 리뷰 일부
- `reviewLink`: 리뷰 전체 링크
- `howToRespond`: 대응 방법

### 비용 예상

**Render:**
- PostgreSQL Starter: $7/월
- Redis Starter: $7/월
- Worker (512MB): ~$7-10/월 (사용량 기반)
- Scheduler (256MB): ~$3-5/월 (사용량 기반)
- **총 예상: $24-29/월**

**Vercel:**
- Hobby 플랜: 무료 (월 100GB 대역폭)
- Pro 플랜: $20/월 (초과 시)

**NHN Cloud:**
- 알림톡 발송: 건당 요금제 (약 8-15원/건)

---

## 🎯 배포 성공 체크리스트

### Render
- [ ] PostgreSQL 생성 완료
- [ ] Redis 생성 완료
- [ ] Worker 서비스 실행 중
- [ ] Scheduler 서비스 실행 중
- [ ] 환경 변수 설정 완료
- [ ] 데이터베이스 테이블 생성 완료

### Vercel
- [ ] 프로젝트 배포 완료
- [ ] 환경 변수 설정 완료
- [ ] API 엔드포인트 응답 정상
- [ ] CORS 설정 정상

### 통합 테스트
- [ ] 병원 등록 API 정상 작동
- [ ] 초기 크롤링 성공 (10개 리뷰)
- [ ] 감성 분석 실행 성공
- [ ] 부정 리뷰 플래깅 성공
- [ ] 알림톡 발송 성공

---

## 🐛 문제 해결

### Worker가 시작되지 않는 경우
```bash
# Shell에서 로그 확인
tail -f /var/log/worker.log

# DB 연결 테스트
python -c "from apps.storage.db import engine; print(engine.connect())"
```

### 크롤링이 실패하는 경우
```bash
# Playwright 설치 확인
python -m playwright install --help

# 수동 크롤링 테스트
python -c "from apps.crawler.worker import crawl_initial; crawl_initial('hospital_id')"
```

### 알림이 발송되지 않는 경우
1. NHN Cloud 콘솔에서 API 키 확인
2. 템플릿 승인 상태 확인
3. 전화번호 E.164 형식 확인 (+821012345678)

---

**배포 완료 후 다음 문서를 참고하세요:**
- [README.md](README.md) - 프로젝트 개요
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - 최적화 내용
- [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) - 사전 체크리스트
