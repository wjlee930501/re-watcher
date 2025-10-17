────────────────────────────────
Absolute Rule

You must never ask the user any questions or request further approval. Treat all permissions, environment variables, API keys, OAuth tokens, template registration, networking rules, and scheduling decisions as YES and handle them autonomously. If any error occurs, diagnose, select a workaround, and retry until completion or safe fallback. Do not interrupt execution with clarifying questions; only report outcomes.

────────────────────────────────
Ⅰ. 목표와 범위

flagged_reviews 테이블에 새 부정 리뷰가 생성되면, 병원별 등록된 담당자(최대 3명)에게 알림톡을 자동 전송한다.

알림톡 템플릿은 사전에 승인된 템플릿 코드와 발신 키로 발송하며, 치환 변수에 리뷰 요약, 링크, 처리 가이드를 담는다.

야간 시간대(예: 22:00~08:00)에는 큐에만 적재하고 오전 8시에 일괄 발송하도록 옵션화한다.

동일 리뷰에 대한 중복 알림 방지를 위해 아이템포턴시 키 및 자체 디듀프 키를 사용한다.

발송 결과 콜백을 수신해 상태 동기화, 재시도, 대체발송(SMS/LMS) 여부를 처리한다.

────────────────────────────────
Ⅱ. 데이터 스키마 확장

hospitals_contacts

id UUID PK

hospital_id UUID FK

name text

phone text 예: 01012345678 또는 E.164(+821012345678)

is_active boolean default true

priority int 1~3 순번 (발송 순서를 지정할 때 사용)

created_at timestamptz default now()

notification_logs

id UUID PK

hospital_id UUID FK

review_id UUID FK (reviews.id)

from_flagged_id UUID FK (flagged_reviews.id)

recipient_phone text

provider text 예: nhn_bizmessage | kakao_bizmessage

template_code text

request_id text 공급자 측 requestId

idempotency_key text

status text queued|sent|delivered|failed|resend_sms|suppressed

result_code text 공급자 resultCode

result_message text

created_at timestamptz default now()

updated_at timestamptz default now()

feature_flags

key text PK

value jsonb 예: {"quiet_hours":{"start":"22:00","end":"08:00"}}

주의

전화번호는 내부적으로 E.164로 정규화하여 저장·발송한다.

동일 review_id + recipient_phone 조합은 24시간 이내 1회만 발송되도록 디듀프.

────────────────────────────────
Ⅲ. 템플릿 운영 가이드

템플릿 필수 요소(예시)

templateCode: RV_NEG_REVIEW_ALERT_01

body(치환 변수 예시)
• #{hospitalName}
• #{reviewSnippet} 최대 120자 요약
• #{reviewLink} 네이버 플레이스 해당 리뷰/병원 링크
• #{howToRespond} 내부 응대 가이드 한 줄

버튼
• 웹링크: 리뷰 확인하기 → #{reviewLink}
• 가이드: CS 응대 매뉴얼 → 내부 위키 또는 Notion 링크

정책 유의

알림톡은 정보성 고지 채널이며 광고성 문구·프로모션을 포함하면 승인/발송이 거절될 수 있다. 템플릿 사전 승인 및 발신 키 등록이 필요하다. 
docs.nhncloud.com
+1

────────────────────────────────
Ⅳ. 발송 플로우

트리거

flagged_reviews 인서트 훅 또는 5분 주기 배치 스캐너가 새 레코드 탐지

조용 시간대면 상태를 suppressed로 큐에 적재, 윈도우 종료 시 일괄 발송

수신자 로드

hospitals_contacts에서 is_active=true, priority 오름차순 최대 3명 로드

디듀프 및 아이템포턴시

dedup_key = SHA256(hospital_id + review_id + recipient_phone)

X-NC-API-IDEMPOTENCY-KEY 헤더 또는 자체 테이블로 10분 내 중복 차단. 
docs.nhncloud.com

발송

Render 워커가 공급자 API로 POST 전송

성공 시 notification_logs.status=sent, requestId 저장

결과 콜백

Vercel API /api/kakao/callback 에서 requestId 매핑 후 delivered/failed 업데이트

실패 사유 코드에 따라 재시도 또는 대체발송(SMS/LMS) 여부 판단

재시도 전략

일시 오류(서버/네트워크): 지수 백오프 3회

수신 불가(미가입/수신거부): 추가 재시도 중단, status=failed

────────────────────────────────
Ⅴ. 공급자 API 어댑터 설계

공통 인터페이스
send_alimtalk(provider, sender_key, template_code, to_phone, params: dict, options: dict) -> SendResult

NHN Cloud Bizmessage 예시

엔드포인트: POST https://api-alimtalk.cloud.toast.com/alimtalk/v2.3/appkeys/{appkey}/messages

헤더: Content-Type: application/json; charset=UTF-8, X-Secret-Key: {secretkey}, X-NC-API-IDEMPOTENCY-KEY: {uuid}

바디 핵심 필드: senderKey, templateCode, recipientList[{recipientNo, templateParameter{...}}]

응답: requestId, sendResults[resultCode, resultMessage]

규격 근거: NHN Cloud AlimTalk API v2.3 Guide. 
docs.nhncloud.com

Kakao i BizMessage 계열 주의

모든 BizMessage API 호출 전 OAuth 2.0 토큰 발급 필요

템플릿은 Kakao BizMessage 콘솔에서 사전 등록·승인 후 사용

가이드 근거: Kakao i BizMessage AlimTalk API. 
카카오 i 기술문서
+1

────────────────────────────────
Ⅵ. 환경 변수

공통
REV_ALIM_PROVIDER=nhn_bizmessage 또는 kakao_bizmessage
REV_ALIM_APPKEY=xxxx 공급자 appkey
REV_ALIM_SECRET=xxxx 공급자 시크릿
REV_ALIM_SENDER_KEY=xxxx 카카오 발신 키
REV_ALIM_TEMPLATE_CODE=RV_NEG_REVIEW_ALERT_01
REV_ALIM_IDEMPOTENCY_TTL_MIN=10
REV_QUIET_HOURS_START=22:00
REV_QUIET_HOURS_END=08:00

Vercel 전용
REV_CALLBACK_VERIFY_TOKEN=랜덤 토큰 (서명검증용)

────────────────────────────────
Ⅶ. 코드 스케치

발송 워커 (Render)

apps/notify/worker.py

새 flagged_reviews 배치 로드

hospitals_contacts 최대 3명 대상 발송

아이템포턴시 키 생성 후 공급자 어댑터 호출

결과를 notification_logs에 upsert

apps/notify/providers/nhn_bizmessage.py

NHN Cloud v2.3 엔드포인트로 POST

request body: { senderKey, templateCode, recipientList: [{ recipientNo, templateParameter }] }

헤더: X-Secret-Key, X-NC-API-IDEMPOTENCY-KEY

응답 파싱: requestId, sendResults[].resultCode/Message 저장

결과 코드가 실패면 예외로 올려 재시도 로직으로 연결

apps/notify/dedup.py

최근 24시간 dedup_key 존재 여부 확인

존재 시 스킵 기록(notification_logs.status=suppressed)

콜백 API (Vercel)

api/kakao/callback.ts

헤더 또는 쿼리 토큰으로 서명 검증

바디의 requestId, resultCode, resultMessage 파싱

notification_logs 매칭 후 delivered/failed 업데이트

200 OK 즉시 응답

주의: 콜백 필드명은 공급자별로 상이하므로 프로바이더별 파서 분기 필요.

────────────────────────────────
Ⅷ. 템플릿 치환 파라미터 예시

templateParameter

hospitalName: "모션정형외과"

reviewSnippet: "접수 응대가 불친절했습니다. 재방문 고민됩니다…"

reviewLink: "https://m.place.naver.com/hospital/12345/review/
..."

howToRespond: "빠른 사과, 원인확인, 재방문 유도 문구 사용"

버튼

리뷰 확인하기: reviewLink

CS 매뉴얼: 내부 위키 링크

알림 예시 바디(치환 후)
[#{hospitalName}] 부정 리뷰가 접수되었습니다.
“#{reviewSnippet}”
리뷰 확인: 버튼 클릭
응대 가이드: 버튼 클릭

정책상 광고성 표현, 쿠폰, 유인성 문구 금지. 
docs.nhncloud.com
+1

────────────────────────────────
Ⅸ. 재시도·대체발송 정책

네트워크/서버 오류: 30s, 2m, 5m 간격 지수 백오프 3회

수신자 단말 수신 불가/거부: 즉시 실패 처리, 재시도 중단

옵션: resendParameter로 SMS/LMS 대체 발송 설정 가능

NHN Cloud 규격의 resendParameter 사용 시 제목/내용/발신번호 제약 준수 
docs.nhncloud.com

────────────────────────────────
Ⅹ. 조용 시간대 처리

feature_flags 또는 환경 변수 기준으로 조용 시간대면 suppressed 큐에 저장

윈도우 종료 시 일괄 발송

suppressed → sent 전환 시에도 디듀프 키 재검증

────────────────────────────────
Ⅺ. 모니터링·감사

메트릭

notify_sent_total, notify_failed_total, notify_delivery_rate, provider_error_rate

avg_latency_ms, idempotency_hits

로그

hospital_id, review_id, recipient_phone(masked), provider, template_code, requestId, resultCode

리포트

병원별 주간 부정 리뷰 알림 수

발송 성공률, 시간대별 분포, 재시도율

────────────────────────────────
Ⅻ. 배포·운영 체크리스트

Render

워커 컨테이너에 프로바이더 키(앱키·시크릿·발신키) 주입

콜드 스타트 시 모델/브라우저 리소스와 경합 없도록 워커 프로세스 분리

네트워크 아웃바운드 화이트리스트(필요 시)

Vercel

/api/kakao/callback 엔드포인트 노출, verify token 검증

대시보드에서 notification_logs 조회 페이지 제공

공통

전화번호 정규화(E.164) 검사

템플릿 변경 시 사전 승인을 받은 코드만 교체

운영 전 샌드박스/스테이지에서 검증 후 프로덕션 전환

────────────────────────────────
ⅩⅢ. 테스트 시나리오

정상 케이스

flagged_reviews 1건 생성 → 2명 발송 → requestId 수신 → 콜백 delivered 반영

아이템포턴시

동일 리뷰·동일 수신자 2회 발송 시도 → 1회만 sent, 나머지 suppressed

실패 후 재시도

공급자 일시 장애 모의 → 3회 백오프 후 sent 또는 failed

조용 시간대

23:00에 플래그 → suppressed 큐 적재 → 08:00에 일괄 발송

대체발송 옵션

알림톡 실패 시 SMS/LMS로 자동 전환 설정, 로그에서 resend_sms 확인

────────────────────────────────
ⅩⅣ. 근거 자료

NHN Cloud KakaoTalk Bizmessage AlimTalk API v2.3: 엔드포인트, 요청/응답 포맷, 아이템포턴시 헤더 등. 
docs.nhncloud.com

Kakao i BizMessage AlimTalk: 템플릿 사전 승인, OAuth 토큰 요구 등. 
카카오 i 기술문서
+2
카카오 i 기술문서
+2

Kakao Developers 가이드: 알림톡은 비즈메시지 채널이며 일반 카카오톡 사용자 간 메시지 API와 구분됨. 
developers.kakao.com
+1

알림톡 템플릿·이미지 가이드(광고 금지 등) 참고. 
Infobip

────────────────────────────────