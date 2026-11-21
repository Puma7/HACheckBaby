# CheckBaby vital engine: breathing-movement hint over MQTT. Not a medical device.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# PyAV wheels bundle FFmpeg, so no system packages are needed.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY checkbaby_engine ./checkbaby_engine

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin engine
USER 10001

# Python as PID 1 receives SIGTERM directly and then publishes "offline".
CMD ["python", "-m", "checkbaby_engine"]
