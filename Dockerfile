FROM python:3.9-slim AS builder

WORKDIR /app
ADD . /app

RUN apt-get update
RUN apt-get install make

ENV PIPENV_VENV_IN_PROJECT=1
RUN make build

# queuerd
FROM builder AS queuerd

CMD [ "make", "queuerd" ]

# Web app
FROM builder AS web

EXPOSE 8000
CMD [ "make", "web" ]
