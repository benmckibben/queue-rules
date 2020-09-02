FROM python:3.8-slim AS builder

WORKDIR /app
ADD . /app

RUN apt-get update
RUN apt-get install make

ENV PIPENV_VENV_IN_PROJECT=1
RUN make build

# Web app
FROM builder AS web

EXPOSE 8000
CMD [ "make", "app" ]

# queuerd
FROM builder AS queuerd

CMD [ "make", "queuerd" ]
