FROM python:3.13-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt \
 && pip install --prefix=/install gunicorn


FROM python:3.13-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/sarteta/ai-voice-agent-twilio-claude"
LABEL org.opencontainers.image.description="Twilio Voice + Claude + ElevenLabs voice agent with calendar tool-use"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=5000

RUN groupadd --system --gid 10001 app \
 && useradd  --system --uid 10001 --gid app --create-home app

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=app:app src ./src

USER app

EXPOSE 5000

# Use gunicorn for production; one worker per CPU is the operator's call.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --access-logfile - voice_agent.app:app"]
