# 빠른 시작 가이드 (Quick Start)

## 🎯 로컬 환경 설정 완료!

로컬 환경에서 이미 완료된 작업:
- ✅ Python 3.13.2 설치
- ✅ 모든 의존성 설치 완료
- ✅ Playwright Chromium 설치 완료
- ✅ Git 저장소 초기화 완료
- ✅ 환경 변수 템플릿 생성 완료

---

## 📝 다음 단계

### 1. GitHub 저장소 생성 및 푸시

```bash
# GitHub에서 새 저장소 생성 후
git remote add origin https://github.com/YOUR_USERNAME/re-watcher.git
git branch -M main
git push -u origin main
```

### 2. 필수 외부 서비스 준비

#### A. NHN Cloud 설정
1. [NHN Cloud](https://www.nhncloud.com) 가입
2. Bizmessage 서비스 활성화
3. 앱키, 시크릿 키 발급
4. 카카오 발신 키 등록
5. 알림톡 템플릿 등록 및 승인 대기

#### B. Render 설정
1. [Render.com](https://render.com) 가입
2. GitHub 계정 연동

#### C. Vercel 설정
1. [Vercel.com](https://vercel.com) 가입
2. GitHub 계정 연동

### 3. 배포 시작

**자세한 배포 가이드는 다음 문서를 참고하세요:**
- [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) - 배포 전 체크리스트
- [DEPLOYMENT.md](DEPLOYMENT.md) - 상세 배포 가이드

---

## 🚨 중요 사항

### 배포 전 반드시 준비해야 할 것:

1. **NHN Cloud 키 3개**
   - APPKEY
   - SECRET
   - SENDER_KEY

2. **알림톡 템플릿 승인**
   - 템플릿 코드: `RV_NEG_REVIEW_ALERT_01`
   - 승인 완료 확인

3. **API 인증 토큰 2개 생성**
   - REV_INTERNAL_API_TOKEN (내부 API용)
   - REV_CALLBACK_VERIFY_TOKEN (콜백용)

---

## 📂 프로젝트 구조

```
re-watcher/
├── apps/              # 메인 애플리케이션
│   ├── common/        # 공통 설정
│   ├── crawler/       # Phase 1: 크롤러
│   ├── storage/       # DB 모델
│   ├── sentiment/     # Phase 2: 감성 분석
│   └── notify/        # Phase 3: 알림 발송
├── api/               # Vercel API
├── scripts/           # 유틸리티 스크립트
├── Dockerfile         # Render 배포용
├── render.yaml        # Render 설정
├── vercel.json        # Vercel 설정
└── .env               # 로컬 환경 변수
```

---

## 🔗 유용한 링크

- [README.md](README.md) - 프로젝트 소개
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 구현 요약
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - 리팩터링 요약
- [DEPLOYMENT.md](DEPLOYMENT.md) - 배포 가이드
- [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) - 체크리스트

---

## 💡 로컬 테스트 (선택)

로컬에서 테스트하려면:

1. PostgreSQL 설치 및 실행
2. Redis 설치 및 실행
3. `.env` 파일에 DB URL 설정
4. 데이터베이스 초기화:
```bash
python scripts/init_db.py
```

5. Worker 실행:
```bash
celery -A apps.scheduler.main worker --loglevel=INFO --concurrency=2
```

---

**준비가 되면 [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md)를 열어 배포를 시작하세요!** 🚀
