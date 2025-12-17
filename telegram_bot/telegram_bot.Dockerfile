FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY Makefile .
COPY *.py .
COPY graph_ticker ./graph_ticker

RUN python -m pip install --upgrade pip

RUN apt-get update && \
    apt-get install -y make ffmpeg

CMD ["make"]

EXPOSE 8506