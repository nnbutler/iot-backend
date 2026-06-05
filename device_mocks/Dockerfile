FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mock_device.py .

# Default: run one device
ENTRYPOINT ["python", "mock_device.py"]
CMD ["--device-id", "docker-device-001", "--backend-url", "https://nginx:443"]
