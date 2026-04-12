FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

EXPOSE 8000

ENV MOCKS_FILE=mocks/example.yaml
ENV PORT=8000

CMD ["python", "server.py"]
