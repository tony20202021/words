#!/bin/bash
# Auto-reload web frontend on .py and .html file changes

cd /home/tony/repos/words/language-learning-bot/web_frontend

exec /home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/watchmedo auto-restart \
    --directory=app \
    --directory=../common \
    --pattern="*.py;*.html" \
    --recursive \
    -- /home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/uvicorn \
        app.main:app --host 0.0.0.0 --port 8800
