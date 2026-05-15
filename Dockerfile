FROM python:3.11-slim

WORKDIR /app/web/backend

COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/backend .

EXPOSE $PORT

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]