FROM python:3.8-slim AS base

WORKDIR /app
ADD . /app

RUN apt-get update
RUN apt-get install make

ENV PIPENV_VENV_IN_PROJECT=1
RUN make build

# Web app
FROM base AS web

EXPOSE 8000
CMD [ "make", "app" ]

# queuerd
FROM base AS queuerd

CMD [ "make", "queuerd" ]
