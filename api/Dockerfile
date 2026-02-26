FROM python:3.12-slim

WORKDIR /app
COPY requirements-api.txt /tmp/requirements-api.txt
RUN pip install --no-cache-dir -r /tmp/requirements-api.txt
COPY api /app/api
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
