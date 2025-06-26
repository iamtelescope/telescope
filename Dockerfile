FROM python:3.12-slim

WORKDIR /opt/telescope

COPY backend/requirements.txt ./

RUN apt-get update && \
    apt-get install -y git gcc build-essential && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt && \
    apt-get purge -y git gcc build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY backend/ .

CMD ["python", "app.py"]
