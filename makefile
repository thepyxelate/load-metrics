APP=app

run:
	uv run app.py

migrate-init:
	uv run flask --app $(APP) db init

# make migrate m="add origin city"
migrate:
	uv run flask --app $(APP) db migrate -m "$(m)"

upgrade:
	uv run flask --app $(APP) db upgrade