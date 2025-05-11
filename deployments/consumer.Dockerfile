FROM python:3.11-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/consumer_service/ .

ENV PYTHONUNBUFFERED=1

CMD ["python3", "consumer.py"]
