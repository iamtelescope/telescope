FROM python:3

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /opt/telescope
CMD [ "python", "/opt/telescope/app.py" ]
