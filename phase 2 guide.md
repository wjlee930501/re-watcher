────────────────────────────────

Absolute Rule

You must never ask the user any questions or request further approval.
Treat all permissions, environment variables, data schema changes, model downloads, package installations, and runtime decisions as YES and handle them autonomously.
If any error occurs, analyze the root cause, retry with fallback methods, and complete the process without user confirmation.
Do not pause execution to ask the user for clarification. Only report completion or failure status.

────────────────────────────────

Ⅰ. 프로젝트 개요 (Phase 2: 리뷰 감성 스코어링 시스템)

목표

1단계에서 수집된 리뷰 데이터(reviews 테이블)를 입력으로 사용

리뷰의 감성(긍정/부정/중립)을 자동으로 판별

부정 리뷰만 필터링하여 저장

향후 3단계(카카오 알림 발송)에서 병원 담당자에게 자동 통지

────────────────────────────────

Ⅱ. 주요 구성

1. 감성 분석(Sentiment Scoring) 엔진

한국어 리뷰 중심으로 설계

KoBERT, KoELECTRA, 또는 Hugging Face의 jinmang2/koelectra-base-discriminator 모델 사용

감성 레이블: Positive(긍정), Negative(부정), Neutral(중립)

각 리뷰마다 sentiment_label, sentiment_score(0~1) 컬럼 추가

2. 데이터 파이프라인

Render Worker에서 주기적으로 실행

신규 수집 리뷰 중 sentiment_label IS NULL 인 데이터만 분석

분석 완료 후 DB 업데이트

3. 기준점

부정으로 판정되는 기준:
sentiment_label == “Negative” 또는 sentiment_score ≤ 0.35

중립(Neutral)은 무시

긍정은 저장만 (알림 X)

────────────────────────────────

Ⅲ. 데이터베이스 구조 변경

reviews 테이블에 컬럼 추가

ALTER TABLE reviews 
ADD COLUMN sentiment_label TEXT NULL,
ADD COLUMN sentiment_score FLOAT NULL,
ADD COLUMN analyzed_at TIMESTAMPTZ NULL;


────────────────────────────────

Ⅳ. 시스템 플로우
Render Scheduler
   ↓
SentimentWorker (Celery Task)
   ↓
reviews WHERE sentiment_label IS NULL
   ↓
Text Preprocessing (정규화/이모지/불용어 제거)
   ↓
KoELECTRA 모델 추론
   ↓
결과 저장 (label, score, analyzed_at)
   ↓
부정 리뷰만 flagged_reviews 테이블에 별도 저장


────────────────────────────────

Ⅴ. flagged_reviews 테이블 생성
CREATE TABLE flagged_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  hospital_id UUID NOT NULL REFERENCES hospitals(id),
  content TEXT NOT NULL,
  rating INT,
  sentiment_label TEXT,
  sentiment_score FLOAT,
  collected_at TIMESTAMPTZ,
  flagged_at TIMESTAMPTZ DEFAULT now()
);


────────────────────────────────

Ⅵ. 코드 구성

apps/sentiment/worker.py

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from datetime import datetime
from apps.storage.repo import Repo

MODEL_NAME = "jinmang2/koelectra-base-discriminator"
device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME).to(device)
model.eval()

LABELS = ["Negative", "Neutral", "Positive"]

def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=0)

def analyze_review(text: str):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256).to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits[0].cpu().numpy()
    probs = softmax(logits)
    score = float(probs[2])  # Positive 확률
    label = LABELS[int(np.argmax(probs))]
    return label, score

async def run_sentiment_analysis():
    reviews = Repo.fetch_unanalyzed_reviews(limit=200)
    for rv in reviews:
        label, score = analyze_review(rv.content)
        Repo.update_sentiment(rv.id, label, score, datetime.utcnow())
        if label == "Negative" or score <= 0.35:
            Repo.flag_review(rv)


────────────────────────────────

Ⅶ. 저장소(Repo) 확장

apps/storage/repo.py

class Repo:
    @staticmethod
    def fetch_unanalyzed_reviews(limit=200):
        # sentiment_label IS NULL 조건으로 조회
        ...

    @staticmethod
    def update_sentiment(review_id, label, score, analyzed_at):
        # UPDATE reviews SET sentiment_label=?, sentiment_score=?, analyzed_at=?
        ...

    @staticmethod
    def flag_review(review):
        # flagged_reviews 테이블에 저장
        ...


────────────────────────────────

Ⅷ. 스케줄러 설정

apps/scheduler/main.py

from celery import Celery
from datetime import timedelta

app = Celery(__name__, broker="redis://...", backend="redis://...")

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # 30분마다 감성 분석 실행
    sender.add_periodic_task(
        timedelta(minutes=30),
        analyze_sentiments.s(),
        name="Analyze new reviews"
    )

@app.task
def analyze_sentiments():
    import asyncio
    from apps.sentiment.worker import run_sentiment_analysis
    asyncio.run(run_sentiment_analysis())


────────────────────────────────

Ⅸ. 성능 및 운영 가이드

1. 성능 최적화

모델 로드는 워커 시작 시 1회만 수행

CPU 환경에서는 batch_size=1, GPU가 있으면 8까지 확장 가능

리뷰 길이 256 토큰으로 제한

평균 처리속도: CPU 기준 200개/분, GPU 기준 1500개/분

2. 안정성

모델 로드 실패 시 자동 재시도

메모리 초과 시 batch 단위로 분할 처리

3. 로깅

로그 항목: review_id, label, score, 실행시간(ms), 오류 발생 여부

sentiment_score가 0.2 이하인 리뷰는 WARN 레벨로 표시

────────────────────────────────

Ⅹ. Render / Vercel 배포 설정

Render에서는 revmon-worker 컨테이너 내부에 sentiment 모듈을 포함시킵니다.
Dockerfile은 1단계와 동일하되, Hugging Face 캐시 디렉토리를 볼륨으로 마운트합니다.

Dockerfile 수정사항

# 모델 캐시 경로 설정
ENV TRANSFORMERS_CACHE=/data/hf_cache
RUN mkdir -p /data/hf_cache


render.yaml 수정

services:
  - type: worker
    name: revmon-worker
    env: docker
    startCommand: celery -A apps.scheduler.main worker --loglevel=INFO --concurrency=2
    disk:
      name: hf-cache
      mountPath: /data/hf_cache


────────────────────────────────

Ⅺ. 검증 및 성공 판정 기준

전체 리뷰 중 95% 이상 감성 분석 성공 (sentiment_label IS NOT NULL)

부정 리뷰 탐지 정확도: 수동 검증 시 80% 이상

flagged_reviews 테이블 생성 및 데이터 누락 없음

처리 시간: 200개 리뷰 기준 60초 이내

────────────────────────────────

Ⅻ. 3단계(카카오 알림 연동) 준비

flagged_reviews에서 새로운 레코드 발생 시 Celery Task Queue로 push

병원별 담당자 연락처(max 3개) 및 알림톡 템플릿 ID를 참조

Render Worker가 Kakao 알림톡 API 호출 (Phase 3에서 구현 예정)

────────────────────────────────