FROM python:3.9

WORKDIR /app

COPY . .

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

EXPOSE 10003

CMD ["gunicorn", "--bind", "0.0.0.0:10003", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "server:app"]