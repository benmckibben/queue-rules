# [Queue Rules](http://queue-rules.trash.house/)
![Queue Rules Build](https://github.com/benmckibben/queue-rules/workflows/Queue%20Rules%20Build/badge.svg?branch=master)
![Queue Rules Publish](https://github.com/benmckibben/queue-rules/workflows/Queue%20Rules%20Publish/badge.svg?branch=master)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview
Queue Rules is an app that lets you define tracks to be queued up after other tracks play. This is accomplished by exposing an **API** allowing users to configure rules and running a **daemon** that watches what users listen to and applies the rules where appropriate. Additionally, the app provides a **Spotify login** flow that handles obtaining tokens for the API and daemon to use to communicate with Spotify.

### Architecture / Dependencies
The core application, database management, and daemon all use [Django](https://www.djangoproject.com/) on Python 3.8. The API is then developed and exposed using [Django Rest Framework](https://www.django-rest-framework.org/). The login flow is handled by [Python Social Auth's Django integration](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html), which in turn links into [`django.contrib.auth`](https://docs.djangoproject.com/en/3.1/ref/contrib/auth/) for handling the core user data.

Other notable dependencies in play:
* [Pipenv](https://docs.pipenv.org/) for Python dependency management.
* [Spotipy](http://spotipy.readthedocs.io/) is used as an abstraction for Spotify's API.
* [Python Decouple](https://github.com/henriquebastos/python-decouple) is used for configuration.
* [Uvicorn](https://www.uvicorn.org/) is currently used as the non-development web server.
* [WhiteNoise](http://whitenoise.evans.io/en/stable/) is used for non-development static file serving, under the assumption that static file caching will be implemented by a CDN.
* [Black](https://github.com/psf/black) and [Flake8](https://flake8.pycqa.org/en/latest/) are used during development to maintain code style and cleanliness.
* [Docker](https://www.docker.com/) is used for containerizing the web app and the daemon for a production environment. It is not currently used in the development workflow.

## Contributing
If you'd like to contribute in some way, please do! There are two things that come to mind that would be helpful ways of doing so.

1. Raise an issue on this repository.
1. Follow the development guide below, and then submit a pull request.

The outstanding things that come to mind that would be nice to have (and I'll probably be working on myself on and off):

1. Decouple the web frontend from the rest of the app. Probably would mean a standalone React app that then interfaces with the API and the auth flow served by Django.
1. Create a new Song model that uses Spotify's track ID as a unique key. Adding this would remove some duplication, but more importantly would enable a way to cache track existence and names. Hitting Spotify's API for these operations causes some costly longer API calls.
1. Utilize Docker in the development workflow.

Outside of these, I'm very open to other ideas!

## Development Guide
If you'd like to run this app yourself and potentially alter code for it, follow the steps below. A Makefile is provided to abstract a few of these steps, so feel free to inspect it if you'd like further details of what it's doing under the hood.

### Initial build
Before running anything, ensure that you have Python 3.8 somewhere on your system. It can be either your system Python, or perhaps a runtime managed by [`pyenv`](https://github.com/pyenv/pyenv).

The command below will attempt to install [Pipenv](https://docs.pipenv.org/) into your system Python install. If you don't want that, alter the Makefile beforehand.

Run `make dev-build`. The command will attempt to install Pipenv (not doing anything if it's already available), then install the standard and development dependencies of the app.

### Create a Spotify app
Navigate to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications), log in, and create a new application.

### Settings
Queue Rules uses [Python Decouple](https://github.com/henriquebastos/python-decouple) for configuration management. See `queue_rules/queue_rules/settings.ini` for an explanation of all of the options you can set and what is strictly required to get a dev app up and running. You can either modify the `settings.ini` file in-place (taking special care not to commit it to version control ever), or set environment variables. See the Python Decouple docs for more details on what you can provide.

A special note on `SPOTIFY_REDIRECT_URI`: at the time of writing, the appropriate route for Spotify to redirect to is `/auth/complete/spotify/`. Prepend this with the host and port you will be accessing your dev app with, and then **register it in your app's settings on the Spotify Developer Dashboard**. If you don't, Spotify will refuse to redirect appropriately to your app.

### Database
Run `make migrate` to run database migrations for the app and its dependencies. If you didn't specify a `DATABASE_URL`, a SQLite database will be created next to `manage.py`.

### Start things up and get coding
Run the development server with `make dev-app`. This command will start up the app server listening on `localhost`/`127.0.0.1` at port `8000`.

You can run a development `queuerd` (the daemon that looks at users' listening activity and applies rules) by running `make queuerd`.

#### A note on frontend development
From here on out, the development workflow centers around the Python codebase. If you choose to contribute to the frontend (either changing the HTML / CSS / JS in-place or redoing the frontend completely), no testing, style, or other guidelines are provided. I am not a frontend developer, so welcome to spaghetti town.

### Formatting and linting
Queue Rules uses [Black](https://github.com/psf/black) for formatting style and [Flake8](https://flake8.pycqa.org/en/latest/) for additional cleanliness checks and static analysis. Builds will fail if these tools are not happy, so get out ahead of that by using `make lint`. This command will first run Black to check for formatting issues, and then if that succeeds, runs Flake8 to see if anything else is off.

You can automatically format your Python code to adhere to Black by running `make format`.

### Testing
At the time of writing, Queue Rules has 100% statement and branch test coverage (...a couple inconsequential files are excluded from the report); please keep it that way!

You can run the tests and generate a coverage report simultaneously by running `make test` (the coverage report will only run if the tests pass). You can then generate an HTML coverage report and serve it by running `make coverage-html` then navigating to [http://localhost:9001/](http://localhost:9001/).

### Docker
At the time of writing, Docker is not typically used for development and is really only used for containerizing the app and daemon for production deployment. If you'd like to build the images, however, here's some examples.

For the web app, something like:
```
docker build -f web.Dockerfile -t queue_rules_web:dev .
```

For `queuerd`, something like:
```
docker build -f queuerd.Dockerfile -t queue_rules_queuerd:dev .
```

### Other Makefile commands
1. `make build`: Install Pipenv, dependencies (excluding those used solely for testing / linting), and run Django's `collectstatic` management command. The last step will create a new directory, `static` next to `manage.py` that contains all of the static files the app needs.
1. `make app`: Run the web app using Uvicorn instead of the Django development server.

## Questions?
Feel free to ask questions by raising issues here, or email me at [dev@trash.house](mailto:dev@trash.house).
