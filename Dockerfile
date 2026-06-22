FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PYTHONPATH="."

# Startup database initialization and seeding is run on FastAPI startup event, 
# so we can directly launch run.py
CMD ["python", "run.py"]
