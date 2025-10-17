# 배포 전 체크리스트 (Pre-Deployment Checklist)

## ✅ 로컬 환경 준비 완료

### 1. 개발 환경 설정
- [x] Python 3.13.2 설치 완료
- [x] pip 25.1.1 설치 완료
- [x] requirements.txt 의존성 설치 완료
- [x] Playwright Chromium 브라우저 설치 완료
- [x] .env 파일 생성 완료 (.env.example 복사)
- [x] Git 저장소 초기화 및 첫 커밋 완료

---

## 📋 배포 전 필수 준비사항

### A. Render 배포 준비

#### 1. Render 계정 및 서비스 설정
- [ ] Render.com 계정 생성
- [ ] GitHub 저장소 생성 및 코드 푸시
- [ ] Render에서 GitHub 연동

#### 2. 데이터베이스 생성
- [ ] Render에서 PostgreSQL 생성
  - Name: `revmon-postgres`
  - Plan: Starter 이상
  - Database: `revmon`
  - User: `revmon`
- [ ] DB URL 확인 및 저장

#### 3. Redis 생성
- [ ] Render에서 Redis 생성
  - Name: `revmon-redis`
  - Plan: Starter 이상
  - Max Memory Policy: `allkeys-lru`
- [ ] Redis URL 확인 및 저장

#### 4. 환경 변수 설정 (필수)
Render Worker 서비스에서 다음 환경 변수를 설정해야 합니다:

**자동 설정 (render.yaml에서):**
- `REV_DB_URL` - PostgreSQL 연결 (자동)
- `REV_REDIS_URL` - Redis 연결 (자동)

**수동 설정 필요:**
- [ ] `REV_ALIM_PROVIDER` - nhn_bizmessage
- [ ] `REV_ALIM_APPKEY` - NHN Cloud 앱키
- [ ] `REV_ALIM_SECRET` - NHN Cloud 시크릿
- [ ] `REV_ALIM_SENDER_KEY` - 카카오 발신 키

#### 5. NHN Cloud Bizmessage 설정
- [ ] NHN Cloud 계정 생성
- [ ] Bizmessage 서비스 활성화
- [ ] 앱키(APPKEY) 발급
- [ ] 시크릿 키(SECRET) 발급
- [ ] 카카오 발신 키(SENDER_KEY) 등록
- [ ] 알림톡 템플릿 등록 및 승인
  - 템플릿 코드: `RV_NEG_REVIEW_ALERT_01`
  - 치환 변수: hospitalName, reviewSnippet, reviewLink, howToRespond

#### 6. Worker 배포
- [ ] render.yaml 설정 확인
- [ ] Docker 이미지 빌드 성공 확인
- [ ] Worker 서비스 시작 확인
- [ ] Scheduler 서비스 시작 확인

---

### B. Vercel 배포 준비

#### 1. Vercel 계정 설정
- [ ] Vercel.com 계정 생성
- [ ] GitHub 저장소 연동

#### 2. 환경 변수 설정 (필수)
Vercel 프로젝트 설정에서 다음 환경 변수를 추가:

- [ ] `REV_DB_URL` - PostgreSQL 연결 URL (Render에서 복사)
- [ ] `REV_REDIS_URL` - Redis 연결 URL (Render에서 복사)
- [ ] `REV_INTERNAL_API_TOKEN` - 내부 API 인증 토큰 (랜덤 생성)
- [ ] `VERCEL_ALLOWED_ORIGINS` - CORS 허용 도메인
- [ ] `REV_CALLBACK_VERIFY_TOKEN` - 콜백 검증 토큰 (랜덤 생성)

**토큰 생성 예시:**
```bash
# PowerShell
-join ((65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 3. 배포 설정
- [ ] vercel.json 설정 확인
- [ ] Build Command: (비워둠)
- [ ] Output Directory: (비워둠)
- [ ] Framework Preset: Other

---

## 🔧 선택적 설정

### 1. 스냅샷 활성화 (선택)
디버깅이 필요한 경우:
```
REV_SNAPSHOT_ENABLED=true
```

### 2. 로그 레벨 조정
디버깅 시:
```
REV_LOG_LEVEL=DEBUG
```

### 3. 배치 크기 조정
메모리가 충분한 경우:
```
REV_SENTIMENT_BATCH_SIZE=32
```

---

## 🧪 배포 전 로컬 테스트

### 1. 데이터베이스 연결 테스트
```bash
# .env 파일에 PostgreSQL URL 설정 후
python scripts/init_db.py
```

### 2. Worker 테스트 (선택)
로컬 PostgreSQL과 Redis가 있는 경우:
```bash
# 터미널 1: Redis 시작
redis-server

# 터미널 2: Celery Worker
celery -A apps.scheduler.main worker --loglevel=INFO --concurrency=2

# 터미널 3: Celery Beat
celery -A apps.scheduler.main beat --loglevel=INFO
```

---

## 📦 GitHub 저장소 준비

### 1. GitHub 저장소 생성
```bash
# GitHub에서 새 저장소 생성 후
git remote add origin https://github.com/YOUR_USERNAME/re-watcher.git
git branch -M main
git push -u origin main
```

### 2. 제외 파일 확인
다음 파일들이 `.gitignore`에 포함되어 있는지 확인:
- [x] `.env`
- [x] `__pycache__/`
- [x] `*.pyc`
- [x] `/data/`
- [x] `.venv/`

---

## 🚀 배포 순서

### 1단계: Render 배포
1. PostgreSQL 생성
2. Redis 생성
3. GitHub 저장소 연결
4. Worker 서비스 배포 (render.yaml 자동 감지)
5. Scheduler 서비스 배포
6. 환경 변수 설정 (NHN Cloud 키 등)
7. Worker 로그 확인

### 2단계: Vercel 배포
1. GitHub 저장소 연결
2. 환경 변수 설정
3. 배포 시작
4. API 엔드포인트 테스트

### 3단계: 통합 테스트
1. 병원 등록 API 호출
```bash
curl -X POST https://your-domain.vercel.app/api/hospitals/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_INTERNAL_TOKEN" \
  -d '{
    "name": "테스트병원",
    "naver_place_url": "https://m.place.naver.com/hospital/example"
  }'
```

2. Render Worker 로그에서 크롤링 확인
3. 30분 후 감성 분석 실행 확인
4. 부정 리뷰 발견 시 알림 발송 확인

---

## 📊 배포 후 모니터링

### 1. Render 대시보드
- [ ] Worker CPU/메모리 사용률 확인
- [ ] 로그에서 에러 확인
- [ ] DB 연결 풀 상태 확인

### 2. Vercel 대시보드
- [ ] 함수 실행 시간 확인
- [ ] 에러율 확인

### 3. 데이터베이스 확인
```sql
-- 병원 수
SELECT COUNT(*) FROM hospitals;

-- 수집된 리뷰 수
SELECT COUNT(*) FROM reviews;

-- 분석된 리뷰 수
SELECT COUNT(*) FROM reviews WHERE sentiment_label IS NOT NULL;

-- 부정 리뷰 수
SELECT COUNT(*) FROM flagged_reviews;

-- 발송된 알림 수
SELECT COUNT(*) FROM notification_logs WHERE status='sent';
```

---

## ⚠️ 주의사항

### 1. 비용 관리
- Render Starter 플랜: $7/월 (DB) + $7/월 (Redis) = $14/월
- Worker 리소스는 사용량에 따라 과금
- Vercel은 무료 플랜 사용 가능

### 2. 보안
- [ ] `.env` 파일이 Git에 커밋되지 않았는지 확인
- [ ] API 토큰이 강력한지 확인 (최소 32자)
- [ ] CORS 설정이 올바른지 확인

### 3. 성능
- 초기 모델 다운로드 시 시간 소요 (5-10분)
- 첫 번째 감성 분석 실행 시 모델 로딩 시간 필요
- Playwright 첫 실행 시 브라우저 초기화 시간 필요

---

## 🎯 배포 성공 기준

### 필수 기능 확인
- [ ] 병원 등록 API 정상 작동
- [ ] 초기 10개 리뷰 수집 성공
- [ ] 1시간 후 증분 크롤링 실행
- [ ] 30분 후 감성 분석 실행
- [ ] 부정 리뷰 플래깅 성공
- [ ] 알림톡 발송 성공 (테스트 번호로)
- [ ] 콜백 수신 성공

### 성능 기준
- [ ] 크롤링 성공률 ≥ 90%
- [ ] 감성 분석 성공률 ≥ 95%
- [ ] 알림 발송 성공률 ≥ 95%
- [ ] 전체 파이프라인 ≤ 3분

---

## 📞 문제 해결

### Render Worker가 시작되지 않는 경우
1. Dockerfile 빌드 로그 확인
2. 환경 변수 설정 확인
3. DB/Redis URL 확인

### Vercel 함수가 실패하는 경우
1. 함수 로그 확인
2. 환경 변수 설정 확인
3. DB 연결 확인

### 알림이 발송되지 않는 경우
1. NHN Cloud 키 확인
2. 템플릿 승인 상태 확인
3. 전화번호 E.164 형식 확인

---

## ✅ 최종 체크

배포 전 다음을 모두 확인하세요:
- [ ] 모든 환경 변수 설정 완료
- [ ] GitHub 저장소 푸시 완료
- [ ] NHN Cloud 키 발급 완료
- [ ] 알림톡 템플릿 승인 완료
- [ ] `.env` 파일이 Git에 포함되지 않음
- [ ] 테스트용 전화번호 준비 완료

**준비가 완료되면 배포를 시작하세요!** 🚀
