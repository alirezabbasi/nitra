import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import psycopg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from psycopg import Connection


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def envelope(payload: dict) -> dict:
    return {
        "message_id": str(uuid.uuid4()),
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "headers": {},
        "payload": payload,
        "retry": None,
    }


def is_message_processed(conn: Connection, service_name: str, message_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM processed_message_ledger
            WHERE service_name = %s AND message_id = %s::uuid
            """,
            (service_name, message_id),
        )
        return cur.fetchone() is not None


def record_message_processed(
    conn: Connection,
    service_name: str,
    message_id: str,
    source_topic: str,
    source_partition: int,
    source_offset: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO processed_message_ledger (
              service_name, message_id, source_topic, source_partition, source_offset
            ) VALUES (%s, %s::uuid, %s, %s, %s)
            ON CONFLICT (service_name, message_id) DO NOTHING
            """,
            (service_name, message_id, source_topic, source_partition, source_offset),
        )
    conn.commit()


async def main() -> None:
    service_name = "backfill_worker"
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    input_topic = env("BACKFILL_INPUT_TOPIC", "gap.events")
    output_topic = env("BACKFILL_REPLAY_TOPIC", "replay.commands")
    group_id = env("BACKFILL_GROUP_ID", "nitra-backfill-worker-v1")
    db_dsn = env("DATABASE_URL", "postgresql://trading:trading@timescaledb:5432/trading")

    conn = psycopg.connect(db_dsn)
    consumer = AIOKafkaConsumer(
        input_topic,
        bootstrap_servers=brokers,
        group_id=group_id,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=brokers)

    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            source_topic = msg.topic
            source_partition = msg.partition
            source_offset = msg.offset

            outer = json.loads(msg.value.decode("utf-8"))
            message_id = outer.get("message_id") or str(uuid.uuid4())
            if is_message_processed(conn, service_name, message_id):
                await consumer.commit()
                continue

            gap = outer.get("payload", {})
            if not gap:
                record_message_processed(conn, service_name, message_id, source_topic, source_partition, source_offset)
                await consumer.commit()
                continue

            replay = {
                "replay_id": str(uuid.uuid4()),
                "source_topic": "raw.market.oanda",
                "start_ts": gap.get("gap_start"),
                "end_ts": gap.get("gap_end"),
                "target_consumer_group": env("BACKFILL_TARGET_GROUP", "nitra-market-normalization-v1"),
                "requested_by": "nitra-backfill-worker",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "dry_run": True,
            }
            await producer.send_and_wait(output_topic, json.dumps(envelope(replay)).encode("utf-8"))
            record_message_processed(conn, service_name, message_id, source_topic, source_partition, source_offset)
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
