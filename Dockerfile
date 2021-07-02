FROM python:3-alpine

COPY ./requirements.txt ./requirements.txt

RUN ["pip", "install", "-r", "./requirements.txt", "--no-cache-dir"]

COPY . .

ENTRYPOINT ["python", "./transfer_artifact_to_ES.py"]
