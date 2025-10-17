# Vercel 환경 변수 설정 스크립트
# PowerShell에서 실행: .\scripts\setup_vercel_env.ps1

Write-Host "=== Vercel 환경 변수 설정 ===" -ForegroundColor Green
Write-Host ""

# 토큰 생성 함수
function New-RandomToken {
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    $token = -join ((1..43) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    return $token
}

Write-Host "필요한 환경 변수를 입력하세요." -ForegroundColor Cyan
Write-Host "(Render 대시보드에서 복사하거나 새로 생성)" -ForegroundColor Gray
Write-Host ""

# 1. Database URL
Write-Host "[1/5] PostgreSQL URL" -ForegroundColor Yellow
Write-Host "Render PostgreSQL의 Internal Database URL을 입력하세요:" -ForegroundColor White
Write-Host "(예: postgresql://revmon:...@...render.com/revmon)" -ForegroundColor Gray
$dbUrl = Read-Host "REV_DB_URL"
if ($dbUrl) {
    Write-Host "설정 중..." -ForegroundColor Gray
    echo $dbUrl | vercel env add REV_DB_URL production
    Write-Host "✓ REV_DB_URL 설정 완료" -ForegroundColor Green
} else {
    Write-Host "⚠ 건너뜀" -ForegroundColor Yellow
}
Write-Host ""

# 2. Redis URL
Write-Host "[2/5] Redis URL" -ForegroundColor Yellow
Write-Host "Render Redis의 Internal Redis URL을 입력하세요:" -ForegroundColor White
Write-Host "(예: redis://...render.com:6379)" -ForegroundColor Gray
$redisUrl = Read-Host "REV_REDIS_URL"
if ($redisUrl) {
    Write-Host "설정 중..." -ForegroundColor Gray
    echo $redisUrl | vercel env add REV_REDIS_URL production
    Write-Host "✓ REV_REDIS_URL 설정 완료" -ForegroundColor Green
} else {
    Write-Host "⚠ 건너뜀" -ForegroundColor Yellow
}
Write-Host ""

# 3. Internal API Token
Write-Host "[3/5] 내부 API 토큰" -ForegroundColor Yellow
Write-Host "새 토큰을 생성할까요? (y/n)" -ForegroundColor White
$generate = Read-Host
if ($generate -eq "y") {
    $apiToken = New-RandomToken
    Write-Host "생성된 토큰: $apiToken" -ForegroundColor Cyan
    Write-Host "⚠ 이 토큰을 안전한 곳에 저장하세요!" -ForegroundColor Red
    Write-Host ""
    Write-Host "설정 중..." -ForegroundColor Gray
    echo $apiToken | vercel env add REV_INTERNAL_API_TOKEN production
    Write-Host "✓ REV_INTERNAL_API_TOKEN 설정 완료" -ForegroundColor Green
} else {
    Write-Host "기존 토큰을 입력하세요:" -ForegroundColor White
    $apiToken = Read-Host "REV_INTERNAL_API_TOKEN"
    if ($apiToken) {
        Write-Host "설정 중..." -ForegroundColor Gray
        echo $apiToken | vercel env add REV_INTERNAL_API_TOKEN production
        Write-Host "✓ REV_INTERNAL_API_TOKEN 설정 완료" -ForegroundColor Green
    } else {
        Write-Host "⚠ 건너뜀" -ForegroundColor Yellow
    }
}
Write-Host ""

# 4. Callback Verify Token
Write-Host "[4/5] 콜백 검증 토큰" -ForegroundColor Yellow
Write-Host "새 토큰을 생성할까요? (y/n)" -ForegroundColor White
Write-Host "(Render Worker와 동일한 토큰을 사용해야 합니다)" -ForegroundColor Gray
$generate = Read-Host
if ($generate -eq "y") {
    $callbackToken = New-RandomToken
    Write-Host "생성된 토큰: $callbackToken" -ForegroundColor Cyan
    Write-Host "⚠ Render Worker에도 동일한 토큰을 설정하세요!" -ForegroundColor Red
    Write-Host ""
    Write-Host "설정 중..." -ForegroundColor Gray
    echo $callbackToken | vercel env add REV_CALLBACK_VERIFY_TOKEN production
    Write-Host "✓ REV_CALLBACK_VERIFY_TOKEN 설정 완료" -ForegroundColor Green
} else {
    Write-Host "Render에서 사용 중인 토큰을 입력하세요:" -ForegroundColor White
    $callbackToken = Read-Host "REV_CALLBACK_VERIFY_TOKEN"
    if ($callbackToken) {
        Write-Host "설정 중..." -ForegroundColor Gray
        echo $callbackToken | vercel env add REV_CALLBACK_VERIFY_TOKEN production
        Write-Host "✓ REV_CALLBACK_VERIFY_TOKEN 설정 완료" -ForegroundColor Green
    } else {
        Write-Host "⚠ 건너뜀" -ForegroundColor Yellow
    }
}
Write-Host ""

# 5. CORS Origins
Write-Host "[5/5] CORS 허용 도메인" -ForegroundColor Yellow
Write-Host "대시보드 도메인을 입력하세요 (쉼표로 구분):" -ForegroundColor White
Write-Host "(예: https://dashboard.example.com,https://admin.example.com)" -ForegroundColor Gray
$origins = Read-Host "VERCEL_ALLOWED_ORIGINS"
if ($origins) {
    Write-Host "설정 중..." -ForegroundColor Gray
    echo $origins | vercel env add VERCEL_ALLOWED_ORIGINS production
    Write-Host "✓ VERCEL_ALLOWED_ORIGINS 설정 완료" -ForegroundColor Green
} else {
    Write-Host "⚠ 건너뜀 (모든 도메인 허용)" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "=== 환경 변수 설정 완료 ===" -ForegroundColor Green
Write-Host ""
Write-Host "설정된 환경 변수 확인:" -ForegroundColor Cyan
vercel env ls
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  1. 환경 변수 확인" -ForegroundColor White
Write-Host "  2. Render Worker에 REV_CALLBACK_VERIFY_TOKEN 설정" -ForegroundColor White
Write-Host "  3. .\scripts\deploy_vercel.ps1 실행하여 배포" -ForegroundColor White
Write-Host ""
