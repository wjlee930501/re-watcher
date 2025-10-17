# 배포 완료 가이드

## 🎉 준비 완료!

모든 로컬 환경 설정과 코드 작성이 완료되었습니다.
GitHub 저장소도 생성되어 코드가 푸시되었습니다.

**Repository**: https://github.com/wjlee930501/re-watcher

---

## 📋 배포 순서

### 1단계: Render 배포 (Backend Worker & Scheduler)

#### A. PostgreSQL 생성
1. [Render Dashboard](https://dashboard.render.com) 접속
2. "New +" → "PostgreSQL" 선택
3. 설정값 입력:
   ```
   Name: revmon-postgres
   Database: revmon
   User: revmon
   Region: Singapore (또는 가장 가까운 리전)
   PostgreSQL Version: 17
   Plan: Starter ($7/month)
   ```
4. "Create Database" 클릭
5. 생성 완료 후 **"Internal Database URL"** 복사
   - 형식: `postgresql://revmon:xxxxx@xxxxx.render.com/revmon`
   - 이 URL은 나중에 사용됩니다

#### B. Redis 생성
1. "New +" → "Redis" 선택
2. 설정값 입력:
   ```
   Name: revmon-redis
   Region: Singapore (PostgreSQL과 동일한 리전 선택)
   Plan: Starter ($7/month)
   Max Memory Policy: allkeys-lru
   ```
3. "Create Redis" 클릭
4. 생성 완료 후 **"Internal Redis URL"** 복사
   - 형식: `redis://xxxxx.render.com:6379`
   - 이 URL은 나중에 사용됩니다

#### C. Blueprint로 Worker & Scheduler 배포
1. "New +" → "Blueprint" 선택
2. "Connect a repository" 클릭
3. GitHub 계정 연동 (처음이라면)
4. `wjlee930501/re-watcher` 저장소 선택
5. Render가 자동으로 `render.yaml` 파일을 감지합니다
6. "Apply" 클릭
7. 2개의 서비스가 생성됩니다:
   - `revmon-worker` (백그라운드 작업 처리)
   - `revmon-scheduler` (주기적 작업 스케줄링)

#### D. 환경 변수 설정

**Worker 서비스** 대시보드로 이동:
1. "Environment" 탭 클릭
2. 다음 환경 변수 추가:

```bash
# NHN Cloud Bizmessage 설정 (필수)
REV_ALIM_PROVIDER=nhn_bizmessage
REV_ALIM_APPKEY=<NHN Cloud에서 발급받은 앱키>
REV_ALIM_SECRET=<NHN Cloud에서 발급받은 시크릿 키>
REV_ALIM_SENDER_KEY=<카카오톡 발신 키>

# 알림톡 템플릿 코드 (기본값 사용 가능)
REV_ALIM_TEMPLATE_CODE=RV_NEG_REVIEW_ALERT_01

# 콜백 검증 토큰 (새로 생성)
REV_CALLBACK_VERIFY_TOKEN=<랜덤 생성한 토큰>
```

**토큰 생성 방법** (PowerShell):
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Scheduler 서비스**도 동일하게 설정

3. "Save Changes" 클릭
4. 서비스가 자동으로 재시작됩니다

#### E. 데이터베이스 초기화

Worker 서비스 대시보드:
1. "Shell" 탭 클릭
2. 다음 명령어 입력:
```bash
python scripts/init_db.py
```

3. 성공 메시지 확인:
```
✅ All tables created successfully!
Created tables: hospitals, reviews, flagged_reviews, notification_logs
```

#### F. 서비스 동작 확인

**Worker 로그** ("Logs" 탭):
```
[INFO] celery@revmon-worker ready.
[INFO] Connected to redis://...
```

**Scheduler 로그**:
```
[INFO] beat: Starting...
[INFO] Scheduler: Sending due task crawl-incremental
```

---

### 2단계: Vercel 배포 (API Endpoints)

#### A. Vercel 로그인

PowerShell에서:
```powershell
cd c:\Users\a\Documents\projects\re-watcher
vercel login
```

브라우저에서 인증 완료

#### B. 환경 변수 설정

제공된 스크립트 실행:
```powershell
.\scripts\setup_vercel_env.ps1
```

스크립트가 다음을 설정합니다:
1. **REV_DB_URL** - Render PostgreSQL URL
2. **REV_REDIS_URL** - Render Redis URL
3. **REV_INTERNAL_API_TOKEN** - 내부 API 토큰 (새로 생성 또는 입력)
4. **REV_CALLBACK_VERIFY_TOKEN** - 콜백 검증 토큰 (Render와 동일)
5. **VERCEL_ALLOWED_ORIGINS** - CORS 허용 도메인

수동으로 설정하려면:
```bash
vercel env add REV_DB_URL production
# 붙여넣기: postgresql://revmon:...@...render.com/revmon

vercel env add REV_REDIS_URL production
# 붙여넣기: redis://...render.com:6379

vercel env add REV_INTERNAL_API_TOKEN production
# 붙여넣기: 생성한 토큰

vercel env add REV_CALLBACK_VERIFY_TOKEN production
# 붙여넣기: Render와 동일한 토큰

vercel env add VERCEL_ALLOWED_ORIGINS production
# 붙여넣기: https://your-dashboard.vercel.app
```

#### C. 프로덕션 배포

스크립트 실행:
```powershell
.\scripts\deploy_vercel.ps1
```

또는 수동:
```bash
vercel --prod
```

배포 URL 확인:
```
✅ Production: https://re-watcher.vercel.app
```

---

## 🧪 통합 테스트

### 1. API 엔드포인트 테스트

```bash
curl -X POST https://re-watcher.vercel.app/api/hospitals/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <REV_INTERNAL_API_TOKEN>" \
  -d '{
    "name": "테스트병원",
    "naver_place_url": "https://m.place.naver.com/hospital/1234567890",
    "alert_phone": "+821012345678"
  }'
```

**예상 응답**:
```json
{
  "hospital_id": "abc123def456",
  "message": "Hospital registered. Initial crawl task queued."
}
```

### 2. Render Worker 로그 확인

Worker 대시보드 → "Logs" 탭:
```
[INFO] Received task: crawl_initial[abc123]
[INFO] Starting initial crawl for hospital abc123
[INFO] Fetched 10 reviews for hospital abc123
[INFO] Task completed successfully
```

### 3. 데이터베이스 확인

Worker Shell:
```bash
python -c "
from apps.storage.db import get_session
from apps.storage.models import Hospital, Review

with get_session() as session:
    hospitals = session.query(Hospital).count()
    reviews = session.query(Review).count()
    print(f'Hospitals: {hospitals}, Reviews: {reviews}')
"
```

### 4. 30분 후 감성 분석 확인

Scheduler가 자동으로 실행:
```
[INFO] Running sentiment analysis...
[INFO] Analyzing 10 reviews
[INFO] Flagged 2 negative reviews (score ≤ 0.35)
```

### 5. 알림 발송 확인

Worker 로그:
```
[INFO] Sending notification for flagged review
[INFO] Recipient: +821012345678
[INFO] Notification sent successfully
```

등록한 전화번호로 카카오톡 수신 확인

---

## 📊 모니터링

### Render 대시보드

**Worker 메트릭**:
- CPU 사용률: ~30-50% (크롤링 시)
- 메모리: ~300-400MB
- 디스크: ~2-3GB (모델 캐시 포함)

**Scheduler 메트릭**:
- CPU: ~5-10%
- 메모리: ~100-150MB

**PostgreSQL**:
- 연결 수: 5-10개
- 쿼리 성능 모니터링
- 스토리지 사용량

**Redis**:
- 메모리 사용량
- 키 개수 (Celery 작업 큐)
- 명령 처리 속도

### Vercel 대시보드

**Functions**:
- 실행 시간: ~500-2000ms
- 에러율: <1%
- 호출 횟수 추적

---

## 💰 예상 비용

### Render
| 서비스 | 플랜 | 월 비용 |
|--------|------|---------|
| PostgreSQL | Starter | $7 |
| Redis | Starter | $7 |
| Worker (512MB) | 사용량 기반 | ~$7-10 |
| Scheduler (256MB) | 사용량 기반 | ~$3-5 |
| **총계** | | **$24-29** |

### Vercel
- **Hobby 플랜**: 무료 (100GB 대역폭/월)
- **Pro 플랜**: $20/월 (초과 시)

### NHN Cloud
- **알림톡**: 건당 8-15원
- 월 1000건 기준: 약 8,000-15,000원

**예상 월 총 비용: 약 $24-29 + 1만원 = ~4-5만원**

---

## ⚠️ 중요 사항

### NHN Cloud 알림톡 템플릿

배포 전 반드시 템플릿 등록 및 승인 완료 필요:

**템플릿 코드**: `RV_NEG_REVIEW_ALERT_01`

**템플릿 내용**:
```
[#{hospitalName}] 부정 리뷰 알림

#{reviewSnippet}

👉 전체 보기: #{reviewLink}

💡 #{howToRespond}
```

**치환 변수**:
- `hospitalName`: 병원 이름
- `reviewSnippet`: 리뷰 일부 (50자)
- `reviewLink`: 네이버 리뷰 전체 링크
- `howToRespond`: 대응 방법 안내

### 보안

- ✅ `.env` 파일은 Git에 커밋되지 않음 (`.gitignore` 확인됨)
- ✅ API 토큰은 최소 32자 이상
- ✅ CORS 설정으로 허용된 도메인만 접근
- ✅ Callback URL에 검증 토큰 사용

---

## 🐛 문제 해결

### Worker가 시작되지 않는 경우

1. **환경 변수 확인**:
   ```bash
   # Render Worker Shell
   printenv | grep REV_
   ```

2. **DB 연결 테스트**:
   ```bash
   python -c "from apps.storage.db import engine; engine.connect()"
   ```

3. **Redis 연결 테스트**:
   ```bash
   python -c "from celery import Celery; app=Celery(broker='redis://...'); app.connection().ensure_connection()"
   ```

### 크롤링이 실패하는 경우

1. **Playwright 설치 확인**:
   ```bash
   python -m playwright install chromium
   ```

2. **URL 형식 확인**:
   - 올바른 예: `https://m.place.naver.com/hospital/1234567890`
   - 잘못된 예: `https://place.naver.com/...` (m. 누락)

3. **수동 크롤링 테스트**:
   ```bash
   python -c "
   from apps.crawler.worker import crawl_initial
   crawl_initial('hospital_id_here')
   "
   ```

### 감성 분석이 실패하는 경우

1. **모델 다운로드 확인**:
   ```bash
   # 첫 실행 시 5-10분 소요 가능
   # /data/hf_cache 디렉토리 확인
   ls -lh /data/hf_cache
   ```

2. **메모리 부족 시**:
   - 배치 크기 감소: `REV_SENTIMENT_BATCH_SIZE=8`
   - Worker 재시작

### 알림이 발송되지 않는 경우

1. **NHN Cloud 키 확인**:
   - 앱키, 시크릿, 발신 키가 모두 정확한지 확인

2. **템플릿 승인 확인**:
   - NHN Cloud 콘솔에서 템플릿 상태 확인
   - "승인" 상태여야 발송 가능

3. **전화번호 형식**:
   - E.164 형식: `+821012345678`
   - 국가 코드(+82) 포함 필수

4. **조용 시간대**:
   - 22:00-08:00 사이에는 발송 지연됨
   - 다음날 08:00에 일괄 발송

---

## 🎯 배포 성공 체크리스트

### Render
- [ ] PostgreSQL 생성 완료
- [ ] Redis 생성 완료
- [ ] Worker 서비스 실행 중
- [ ] Scheduler 서비스 실행 중
- [ ] 환경 변수 설정 완료
- [ ] 데이터베이스 테이블 생성 완료
- [ ] Worker 로그에 에러 없음

### Vercel
- [ ] 프로젝트 배포 완료
- [ ] 환경 변수 설정 완료
- [ ] API 엔드포인트 응답 정상 (200 OK)
- [ ] CORS 설정 동작 확인

### 통합 테스트
- [ ] 병원 등록 API 성공
- [ ] 초기 크롤링 10개 리뷰 수집 완료
- [ ] 감성 분석 실행 완료
- [ ] 부정 리뷰 플래깅 성공
- [ ] 알림톡 발송 성공 (테스트 번호로)

---

## 📚 추가 문서

- [README.md](README.md) - 프로젝트 개요
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 구현 요약
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - 최적화 내용
- [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) - 사전 체크리스트
- [DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md) - 상세 배포 가이드

---

## 🚀 다음 단계

배포가 완료되면:

1. **모니터링 설정**
   - Render 메트릭 확인
   - Vercel Functions 로그 확인
   - 에러 알림 설정

2. **병원 등록**
   - 실제 병원 URL로 테스트
   - 알림 수신 확인

3. **최적화**
   - 크롤링 주기 조정 (필요시)
   - 감성 분석 임계값 조정
   - 알림 템플릿 개선

4. **확장**
   - 대시보드 UI 개발 (선택)
   - 통계 및 분석 기능 추가
   - 다중 병원 지원 확대

---

**배포 성공을 기원합니다!** 🎉

문제가 발생하면 Render 또는 Vercel 로그를 먼저 확인하세요.
