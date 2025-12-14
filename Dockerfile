# Dockerfile для Competitive Intelligence Tool

FROM python:3.11-slim

WORKDIR /app

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    libssl-dev \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо файли проєкту
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Створюємо необхідні директорії
RUN mkdir -p /data /app/exports /app/logs

# Встановлюємо права
RUN chmod +x run_intelligence.py

# Порт для веб-інтерфейсу
EXPOSE 5000

# За замовчуванням запускаємо веб-сервер
CMD ["python", "src/web/app.py"]
