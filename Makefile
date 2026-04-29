SHELL := /bin/bash

session-bootstrap:
	scripts/session/session-bootstrap.sh

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

test-dev-00025:
	tests/dev-00025/run.sh

test-dev-00026:
	tests/dev-00026/run.sh

test-dev-00027:
	tests/dev-00027/run.sh

test-dev-00028:
	tests/dev-00028/run.sh

test-dev-00029:
	tests/dev-00029/run.sh

test-dev-00030:
	tests/dev-00030/run.sh

test-dev-00031:
	tests/dev-00031/run.sh

test-dev-00032:
	tests/dev-00032/run.sh

test-dev-00033:
	tests/dev-00033/run.sh

test-dev-00034:
	tests/dev-00034/run.sh

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

test-dev-0017:
	tests/dev-0017/run.sh

test-dev-0018:
	tests/dev-0018/run.sh

test-dev-0019:
	tests/dev-0019/run.sh

test-dev-0020:
	tests/dev-0020/run.sh

test-dev-0021:
	tests/dev-0021/run.sh

test-dev-0022:
	tests/dev-0022/run.sh

test-dev-0023:
	tests/dev-0023/run.sh

test-dev-0036:
	tests/dev-0036/run.sh

test-dev-0037:
	tests/dev-0037/run.sh

test-dev-0038:
	tests/dev-0038/run.sh

test-dev-0039:
	tests/dev-0039/run.sh

test-dev-0040:
	tests/dev-0040/run.sh

test-dev-0041:
	tests/dev-0041/run.sh

test-dev-0042:
	tests/dev-0042/run.sh

test-dev-0043:
	tests/dev-0043/run.sh

test-dev-0044:
	tests/dev-0044/run.sh

test-dev-0045:
	tests/dev-0045/run.sh

db:
	docker compose exec timescaledb psql -U $$POSTGRES_USER -d $$POSTGRES_DB
