FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# La BD se guarda en /data (volumen persistente en Railway)
ENV POKEMON_DB_PATH=/data/tracker.db
ENV FLASK_PORT=8080

EXPOSE 8080

CMD ["python", "app.py"]
