# SkyBlink backend for a Hugging Face Docker Space (free, no card). Port 7860 is what HF expects.
# ONE gunicorn process with threads: blink jobs live in memory.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DEBUG=False \
    ALLOWED_HOSTS=.hf.space,localhost,127.0.0.1 \
    NUM_PROXIES=1 \
    SKYBLINK_MAX_JOBS=1 \
    SKYBLINK_ALLOW_COLD=1 \
    SKYBLINK_CACHE=/tmp/skyblink-cache \
    DATABASE_URL=sqlite:////tmp/db.sqlite3
RUN useradd -m -u 1000 user
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY --chown=user backend backend
COPY --chown=user shared shared
USER user
WORKDIR /app/backend
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput
EXPOSE 7860
# SECRET_KEY should be a Space secret; without one, make a random key per start (the API keeps no logins).
CMD export SECRET_KEY="${SECRET_KEY:-$(python -c 'import secrets; print(secrets.token_urlsafe(50))')}" && \
    python manage.py migrate --noinput && \
    gunicorn skyblink.wsgi:application --bind 0.0.0.0:7860 --workers 1 --threads 8 --timeout 120
