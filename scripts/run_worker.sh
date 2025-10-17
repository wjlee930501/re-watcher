#!/bin/bash
# Run Celery worker for local development

set -e

echo "Starting Celery worker..."
celery -A apps.scheduler.main worker --loglevel=INFO --concurrency=3
