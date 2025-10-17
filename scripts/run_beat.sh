#!/bin/bash
# Run Celery beat scheduler for local development

set -e

echo "Starting Celery beat scheduler..."
celery -A apps.scheduler.main beat --loglevel=INFO
