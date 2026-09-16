FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY proxy-pro/requirements.txt /app/proxy-pro/requirements.txt
RUN pip install --no-cache-dir -r /app/proxy-pro/requirements.txt

COPY proxy-pro /app/proxy-pro

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "gunicorn --chdir /app/proxy-pro wsgi:app --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 30"]
