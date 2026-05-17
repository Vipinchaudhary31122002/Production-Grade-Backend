FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /backend

RUN pip install uv

COPY requirements.txt .
RUN uv pip install -r requirements.txt --system

COPY . .

CMD ["sleep", "infinity"]