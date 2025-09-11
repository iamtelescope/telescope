FROM node:20 AS frontend

WORKDIR /opt/telescope/ui

COPY ui/package*.json ./
RUN npm ci

COPY ui/ .
RUN npm run build


FROM python:3.12-slim AS backend

WORKDIR /opt/telescope

COPY backend/requirements.txt ./

RUN apt-get update && \
    apt-get install -y git gcc build-essential && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt && \
    apt-get purge -y git gcc build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY backend/ .

COPY --from=frontend /opt/telescope/ui/dist/static ./telescope/static/
COPY --from=frontend /opt/telescope/ui/dist/favicon.ico ./telescope/static/
COPY --from=frontend /opt/telescope/ui/dist/editor.worker.js ./telescope/static/
COPY --from=frontend /opt/telescope/ui/dist/editor.worker.js.map ./telescope/static/
COPY --from=frontend /opt/telescope/ui/dist/json.worker.js ./telescope/static/
COPY --from=frontend /opt/telescope/ui/dist/json.worker.js.map ./telescope/static/
COPY --from=frontend /opt/telescope/ui/src/assets/namedlogo.png ./telescope/static/
COPY --from=frontend /opt/telescope/ui/dist/index.html ./telescope/templates/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


FROM python:3.12-slim AS base

ENV DJANGO_COLLECTSTATIC=1

WORKDIR /opt/telescope

COPY --from=backend /usr/local /usr/local
COPY --from=backend /opt/telescope /opt/telescope
COPY --from=backend /entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["python", "app.py"]
