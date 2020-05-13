FROM python:alpine3.11

COPY requirements.txt /app/

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT python ./app/cleanup-reminder.py