FROM python:latest

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y iputils-ping && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

CMD ["bash"]
