SHELL := /bin/bash

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

restart:
	docker compose restart

init:
	docker compose exec minio sh -c "mc alias set local http://localhost:9000 $$MINIO_ROOT_USER $$MINIO_ROOT_PASSWORD && mc mb -p local/mlflow || true"

reset:
	docker compose down -v

kafka-topics:
	docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list

kafka-bootstrap:
	scripts/kafka/bootstrap-topics.sh

test-dev-00003:
	tests/dev-00003/run.sh

db:
	docker compose exec timescaledb psql -U $$POSTGRES_USER -d $$POSTGRES_DB
