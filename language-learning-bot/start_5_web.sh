#!/bin/bash
# Start Web Frontend on port 8548
set -e
cd "$(dirname "$0")/web_frontend"

export BLS_URL="${BLS_URL:-http://localhost:8531}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:8573}"
# Ключ подписи сессионной куки. Заглушки по умолчанию тут быть не должно:
# она молча работала бы в продакшене, а подделать такую куку тривиально.
if [ -z "${SECRET_KEY:-}" ]; then
  echo "SECRET_KEY не задан. Сгенерируйте и положите в .env:" >&2
  echo "  python -c 'import secrets; print(secrets.token_urlsafe(48))'" >&2
  exit 1
fi
export SECRET_KEY
export WEB_URL="${WEB_URL:-http://localhost:8548}"

echo "Starting Web Frontend on port 8548..."
conda run -n amikhalev_language_learning_bot \
    uvicorn app.main:app --host 0.0.0.0 --port 8548 --reload
