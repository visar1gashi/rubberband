FROM python:3.10-slim

# System deps: ffmpeg + rubberband + libsndfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 rubberband-cli ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

# RunPod serverless runs the Python file; no extra args needed
CMD ["python", "-u", "handler.py"]
