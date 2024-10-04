FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY Makefile .
COPY main.py .

RUN python -m pip install --upgrade pip

RUN apt-get update && \
    apt-get install -y make && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

CMD ["make"]

EXPOSE 8506