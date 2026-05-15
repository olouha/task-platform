FROM node:18-alpine AS frontend

WORKDIR /frontend

COPY web/frontend/package*.json ./
RUN npm install

COPY web/frontend ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/backend .

COPY --from=frontend /frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE ${PORT}

CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}"]