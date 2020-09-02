.PHONY: list
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

build:
	@pip install pipenv && \
	pipenv sync && \
	cd queue_rules && \
	pipenv run python manage.py collectstatic

dev-build:
	@pip install pipenv && \
	pipenv install --dev

migrate:
	@cd queue_rules && pipenv run python manage.py migrate

web:
	@cd queue_rules && pipenv run uvicorn queue_rules.asgi:application $(args)

dev-web:
	@cd queue_rules && pipenv run python manage.py runserver

queuerd:
	@cd queue_rules && pipenv run python manage.py queuerd

test:
	@cd queue_rules && pipenv run coverage run manage.py test && pipenv run coverage report

make coverage-html:
	@cd queue_rules && \
	pipenv run coverage html && \
	cd htmlcov && \
	pipenv run python -m http.server 9001

format:
	@cd queue_rules && pipenv run black .

lint:
	@cd queue_rules && pipenv run black --check . && pipenv run flake8 .

web-image:
	@docker build . --target web $(args)

queuerd-image:
	@docker build . --target queuerd $(args)