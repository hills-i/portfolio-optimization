FROM python:3.13-slim

WORKDIR /app

ENV FLASK_ENV=production \
    DEBUG=false \
    PORT=5000

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 5000

CMD ["python3", "src/run.py"]
