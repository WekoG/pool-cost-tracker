FROM python:3.12-slim

WORKDIR /app
COPY requirements-ui.txt /tmp/requirements-ui.txt
RUN pip install --no-cache-dir -r /tmp/requirements-ui.txt
COPY ui /app/ui

EXPOSE 8501
CMD ["streamlit", "run", "/app/ui/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
