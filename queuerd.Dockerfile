FROM python:3.8-slim

WORKDIR /app
ADD . /app

RUN apt-get update
RUN apt-get install make

ENV PIPENV_VENV_IN_PROJECT=1
RUN make build

CMD [ "make", "queuerd" ]
