import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import psycopg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from ingestion.contracts import build_envelope, is_message_processed, parse_json_bytes, record_message_processed


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


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

            outer = parse_json_bytes(msg.value)
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
            await producer.send_and_wait(output_topic, json.dumps(build_envelope(replay)).encode("utf-8"))
            record_message_processed(conn, service_name, message_id, source_topic, source_partition, source_offset)
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
