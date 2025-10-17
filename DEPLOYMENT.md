# 배포 가이드

이 문서는 병원 리뷰 모니터링 시스템의 배포 절차를 안내합니다.

## 사전 준비

### 1. 필수 계정 및 서비스
- [Render](https://render.com) 계정
- [Vercel](https://vercel.com) 계정
- [NHN Cloud](https://www.nhncloud.com) 계정 (Bizmessage 서비스 활성화)
- 카카오 알림톡 템플릿 사전 승인

### 2. 환경 변수 준비
다음 정보를 미리 준비하세요:
- PostgreSQL 연결 정보
- Redis 연결 정보
- NHN Cloud 앱키, 시크릿, 발신 키
- 알림톡 템플릿 코드
- 내부 API 토큰 (랜덤 생성)
- 콜백 검증 토큰 (랜덤 생성)

---

## Render 배포

### 1. 데이터베이스 및 Redis 생성

1. Render 대시보드 접속
2. "New +" → "PostgreSQL" 선택
   - Name: `revmon-postgres`
   - Database: `revmon`
   - User: `revmon`
   - Plan: Starter 이상
3. "New +" → "Redis" 선택
   - Name: `revmon-redis`
   - Plan: Starter 이상

### 2. Worker 및 Scheduler 배포

1. GitHub 저장소 연결
2. Render가 `render.yaml` 자동 감지
3. 환경 변수 설정:
   - Render 대시보드에서 각 서비스의 환경 변수 섹션으로 이동
   - 다음 변수들을 수동 추가:
     ```
     REV_ALIM_PROVIDER=nhn_bizmessage
     REV_ALIM_APPKEY=your-appkey
     REV_ALIM_SECRET=your-secret
     REV_ALIM_SENDER_KEY=your-sender-key
     ```

4. 배포 시작
   - `revmon-worker`: Celery Worker (크롤링, 감성분석, 알림)
   - `revmon-scheduler`: Celery Beat (스케줄러)

### 3. 데이터베이스 초기화

Worker 배포 완료 후:

1. Render 대시보드 → `revmon-worker` → Shell 탭
2. 다음 명령 실행:
   ```bash
   python scripts/init_db.py
   ```

### 4. 디스크 볼륨 확인

`revmon-worker`에 Hugging Face 모델 캐시용 디스크가 마운트되어 있는지 확인:
- Mount Path: `/data/hf_cache`
- Size: 10GB

---

## Vercel 배포

### 1. 프로젝트 생성

1. Vercel 대시보드 접속
2. "Add New..." → "Project"
3. GitHub 저장소 연결

### 2. 환경 변수 설정

Vercel 프로젝트 설정 → Environment Variables에서 다음 변수 추가:

```
REV_DB_URL=postgresql+psycopg://user:password@host:port/db
REV_REDIS_URL=redis://host:port/0
REV_INTERNAL_API_TOKEN=random-secret-token
VERCEL_ALLOWED_ORIGINS=https://your-domain.vercel.app
REV_CALLBACK_VERIFY_TOKEN=random-callback-token
```

**주의**: Render에서 생성한 PostgreSQL, Redis URL을 사용하세요.

### 3. 빌드 설정

- Framework Preset: Other
- Build Command: (비워둠)
- Output Directory: (비워둠)

### 4. 배포

"Deploy" 버튼 클릭

---

## 배포 확인

### 1. Render 상태 확인

```bash
# Worker 로그 확인
render logs -s revmon-worker

# Scheduler 로그 확인
render logs -s revmon-scheduler
```

다음 로그가 표시되어야 합니다:
- "Periodic tasks configured successfully"
- "Starting Celery worker..."

### 2. Vercel API 테스트

병원 등록 API 테스트:

```bash
curl -X POST https://your-domain.vercel.app/api/hospitals/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_INTERNAL_TOKEN" \
  -d '{
    "name": "테스트병원",
    "naver_place_url": "https://m.place.naver.com/hospital/example"
  }'
```

성공 응답:
```json
{
  "success": true,
  "hospital_id": "uuid",
  "name": "테스트병원",
  "message": "Hospital registered and initial crawl queued"
}
```

### 3. 크롤링 확인

1. 병원 등록 후 약 1분 대기
2. Render Worker 로그 확인:
   ```
   Starting crawl for hospital {id}, initial=True
   Successfully parsed N reviews
   Crawl completed for hospital {id}: N new reviews
   ```

### 4. 감성 분석 확인

크롤링 완료 후 30분 이내:
```
Starting sentiment analysis (limit=200)
Analyzing N reviews
Sentiment analysis complete: N analyzed, M flagged
```

### 5. 알림 발송 확인

부정 리뷰가 감지되면 5분 이내:
```
Processing notification for flagged review: {id}
AlimTalk sent successfully: {request_id}
Notification processing complete: sent=N
```

---

## 문제 해결

### Worker가 시작되지 않음
- Dockerfile 빌드 로그 확인
- Playwright 설치 여부 확인: `python -m playwright install chromium`

### 크롤링 실패
- 네이버 플레이스 URL 형식 확인
- HTTP 403/429 에러: 백오프 재시도 로그 확인
- CAPTCHA 감지: 격리 큐 로그 확인

### 감성 분석 실패
- Hugging Face 모델 다운로드 확인
- 디스크 볼륨 마운트 확인
- 메모리 부족: Worker 인스턴스 업그레이드

### 알림 발송 실패
- NHN Cloud 앱키, 시크릿 확인
- 템플릿 코드 승인 상태 확인
- 전화번호 E.164 형식 확인
- 콜백 엔드포인트 접근 가능 여부 확인

### 데이터베이스 연결 실패
- PostgreSQL URL 형식 확인: `postgresql+psycopg://...`
- Render 대시보드에서 DB 상태 확인
- 네트워크 방화벽 설정 확인

---

## 모니터링

### Render 대시보드
- Metrics 탭: CPU, 메모리, 네트워크 사용량
- Logs 탭: 실시간 로그
- Events 탭: 배포 이력

### 주요 메트릭 확인
```python
# DB 쿼리로 확인
SELECT COUNT(*) FROM reviews;  -- 수집된 리뷰 수
SELECT COUNT(*) FROM reviews WHERE sentiment_label IS NOT NULL;  -- 분석된 리뷰
SELECT COUNT(*) FROM flagged_reviews;  -- 부정 리뷰
SELECT COUNT(*) FROM notification_logs WHERE status='sent';  -- 발송된 알림
```

### 로그 레벨 조정
Worker 환경 변수에서:
```
CELERY_LOG_LEVEL=DEBUG  # 상세 로그
```

---

## 업데이트 배포

### 코드 변경 시

1. GitHub에 푸시
2. Render, Vercel이 자동 배포
3. Worker 재시작 확인

### 의존성 변경 시

1. `requirements.txt` 업데이트
2. GitHub 푸시
3. Render에서 Docker 이미지 재빌드

### DB 스키마 변경 시

1. 마이그레이션 스크립트 작성
2. Render Shell에서 실행:
   ```bash
   python scripts/migrate_db.py
   ```

---

## 보안 체크리스트

- [ ] 모든 API 토큰이 환경 변수로 관리됨
- [ ] `.env` 파일이 `.gitignore`에 포함됨
- [ ] Vercel CORS 설정 확인
- [ ] 콜백 엔드포인트 서명 검증 활성화
- [ ] PostgreSQL 외부 접근 제한
- [ ] Redis 비밀번호 설정

---

## 백업 및 복구

### 데이터베이스 백업

Render 대시보드 → `revmon-postgres` → Backups 탭에서 자동 백업 활성화

수동 백업:
```bash
pg_dump $REV_DB_URL > backup.sql
```

### 복구

```bash
psql $REV_DB_URL < backup.sql
```

---

## 운영 팁

### 성능 최적화
- Worker 동시성 조정: `--concurrency=N`
- 크롤링 간격 조정: `timedelta(hours=N)`
- Redis maxmemory policy: `noeviction`

### 비용 최적화
- Render Starter 플랜으로 시작
- 트래픽 증가 시 Professional 플랜으로 업그레이드
- Disk 볼륨은 필요한 만큼만 할당

### 장애 대응
- Worker 다운: Render가 자동 재시작
- DB 연결 끊김: 자동 재연결 (pool_pre_ping=True)
- Redis 장애: Celery가 재시도 큐에 저장

---

## 지원

문제가 지속되면 다음을 확인하세요:
1. Render 상태 페이지: https://status.render.com
2. Vercel 상태 페이지: https://www.vercel-status.com
3. GitHub Issues: [프로젝트 URL]/issues

---

**배포 성공을 기원합니다!** 🚀
