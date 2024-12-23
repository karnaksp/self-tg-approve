FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY Makefile .
COPY *.py .

RUN python -m pip install --upgrade pip

RUN apt-get update && \
    apt-get install -y make

CMD ["make"]

EXPOSE 8506