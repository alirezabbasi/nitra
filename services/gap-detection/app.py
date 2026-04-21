import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from psycopg import Connection


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
    service_name = "gap_detection"
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    input_topic = env("GAP_INPUT_TOPIC", "bar.1m")
    output_topic = env("GAP_OUTPUT_TOPIC", "gap.events")
    group_id = env("GAP_GROUP_ID", "nitra-gap-detection-v1")
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
    last_bucket: dict[tuple[str, str], datetime] = {}

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

            bar = outer.get("payload", {})
            venue = bar.get("venue")
            symbol = bar.get("canonical_symbol")
            bucket_raw = bar.get("bucket_start")
            if not venue or not symbol or not bucket_raw:
                record_message_processed(conn, service_name, message_id, source_topic, source_partition, source_offset)
                await consumer.commit()
                continue

            bucket = parse_ts(bucket_raw)
            key = (venue, symbol)
            previous = last_bucket.get(key)
            if previous is not None and bucket > previous + timedelta(minutes=1):
                gap_event = {
                    "gap_id": str(uuid.uuid4()),
                    "venue": venue,
                    "canonical_symbol": symbol,
                    "timeframe": "1m",
                    "gap_start": (previous + timedelta(minutes=1)).isoformat(),
                    "gap_end": (bucket - timedelta(minutes=1)).isoformat(),
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "source": "nitra.gap-detection",
                    "reason": "missing_minute_bars",
                }
                await producer.send_and_wait(output_topic, json.dumps(envelope(gap_event)).encode("utf-8"))
            last_bucket[key] = bucket
            record_message_processed(conn, service_name, message_id, source_topic, source_partition, source_offset)
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
