FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Папка для хранения данных (монтируется как volume)
RUN mkdir -p /app/data

CMD ["python", "bot.py"]
