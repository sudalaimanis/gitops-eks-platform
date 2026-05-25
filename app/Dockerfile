FROM python:3.11-slim

# Non-root user for security — created before COPY so --chown works
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

# Install dependencies first — Docker caches this layer
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY --chown=appuser:appuser app.py .

USER appuser

EXPOSE 5000

# gunicorn for production — never use flask dev server in containers
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
