FROM python:3.11-slim

WORKDIR /app

COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/backend .

ENV PORT=8000
EXPOSE ${PORT}

CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}"]