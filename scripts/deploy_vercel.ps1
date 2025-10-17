# Vercel 배포 스크립트
# PowerShell에서 실행: .\scripts\deploy_vercel.ps1

Write-Host "=== Vercel 배포 시작 ===" -ForegroundColor Green
Write-Host ""

# 1. Vercel 로그인 확인
Write-Host "[1/4] Vercel 로그인 확인..." -ForegroundColor Yellow
vercel whoami 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Vercel에 로그인이 필요합니다." -ForegroundColor Red
    Write-Host "다음 명령어를 실행하세요:" -ForegroundColor Cyan
    Write-Host "  vercel login" -ForegroundColor White
    Write-Host ""
    exit 1
}
Write-Host "✓ 로그인 확인 완료" -ForegroundColor Green
Write-Host ""

# 2. 프로젝트 연결 (이미 연결되어 있지 않은 경우)
Write-Host "[2/4] Vercel 프로젝트 연결..." -ForegroundColor Yellow
if (-not (Test-Path ".vercel")) {
    Write-Host "프로젝트를 Vercel에 연결합니다..." -ForegroundColor Cyan
    vercel link
    if ($LASTEXITCODE -ne 0) {
        Write-Host "프로젝트 연결 실패" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ 이미 연결된 프로젝트 발견" -ForegroundColor Green
}
Write-Host ""

# 3. 환경 변수 설정 안내
Write-Host "[3/4] 환경 변수 설정 확인..." -ForegroundColor Yellow
Write-Host ""
Write-Host "다음 환경 변수가 설정되어 있는지 확인하세요:" -ForegroundColor Cyan
Write-Host "  1. REV_DB_URL           - Render PostgreSQL URL" -ForegroundColor White
Write-Host "  2. REV_REDIS_URL        - Render Redis URL" -ForegroundColor White
Write-Host "  3. REV_INTERNAL_API_TOKEN - 내부 API 토큰" -ForegroundColor White
Write-Host "  4. REV_CALLBACK_VERIFY_TOKEN - 콜백 검증 토큰" -ForegroundColor White
Write-Host "  5. VERCEL_ALLOWED_ORIGINS - CORS 허용 도메인" -ForegroundColor White
Write-Host ""

$envCheck = Read-Host "환경 변수가 모두 설정되었습니까? (y/n)"
if ($envCheck -ne "y") {
    Write-Host ""
    Write-Host "환경 변수 설정 방법:" -ForegroundColor Yellow
    Write-Host "  vercel env add REV_DB_URL production" -ForegroundColor White
    Write-Host "  vercel env add REV_REDIS_URL production" -ForegroundColor White
    Write-Host "  vercel env add REV_INTERNAL_API_TOKEN production" -ForegroundColor White
    Write-Host "  vercel env add REV_CALLBACK_VERIFY_TOKEN production" -ForegroundColor White
    Write-Host "  vercel env add VERCEL_ALLOWED_ORIGINS production" -ForegroundColor White
    Write-Host ""
    Write-Host "토큰 생성:" -ForegroundColor Yellow
    Write-Host "  python -c `"import secrets; print(secrets.token_urlsafe(32))`"" -ForegroundColor White
    Write-Host ""
    exit 0
}
Write-Host ""

# 4. 프로덕션 배포
Write-Host "[4/4] 프로덕션 배포 시작..." -ForegroundColor Yellow
Write-Host ""
vercel --prod
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "배포 실패" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== 배포 완료 ===" -ForegroundColor Green
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. Vercel 대시보드에서 배포 확인" -ForegroundColor White
Write-Host "  2. API 엔드포인트 테스트" -ForegroundColor White
Write-Host "  3. Render Worker 로그 확인" -ForegroundColor White
Write-Host ""
Write-Host "API 테스트:" -ForegroundColor Yellow
Write-Host "  curl -X POST https://re-watcher.vercel.app/api/hospitals/register \" -ForegroundColor White
Write-Host "    -H `"Content-Type: application/json`" \" -ForegroundColor White
Write-Host "    -H `"Authorization: Bearer YOUR_TOKEN`" \" -ForegroundColor White
Write-Host "    -d '{`"name`": `"테스트병원`", `"naver_place_url`": `"https://m.place.naver.com/hospital/..`"}'" -ForegroundColor White
Write-Host ""
