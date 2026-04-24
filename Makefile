SHELL := /bin/bash

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

charting-logs:
	docker compose logs -f --tail=200 charting

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

policy-check:
	scripts/policy/check_technology_enforcement.sh
	scripts/policy/check_contract_policy.sh

enforce-section-5-1: policy-check

test-dev-00003:
	tests/dev-00003/run.sh

test-dev-00004:
	tests/dev-00004/run.sh

test-dev-00005:
	tests/dev-00005/run.sh

test-dev-00006:
	tests/dev-00006/run.sh

test-dev-00008:
	tests/dev-00008/run.sh

test-dev-00009:
	tests/dev-00009/run.sh

test-dev-0010:
	tests/dev-0010/run.sh

test-dev-0012:
	tests/dev-0012/run.sh

test-dev-0013:
	tests/dev-0013/run.sh

test-dev-0014:
	tests/dev-0014/run.sh

test-dev-0015:
	tests/dev-0015/run.sh

db:
	docker compose exec timescaledb psql -U $$POSTGRES_USER -d $$POSTGRES_DB
