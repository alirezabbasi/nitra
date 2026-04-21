import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


async def main() -> None:
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    input_topic = env("BACKFILL_INPUT_TOPIC", "gap.events")
    output_topic = env("BACKFILL_REPLAY_TOPIC", "replay.commands")
    group_id = env("BACKFILL_GROUP_ID", "nitra-backfill-worker-v1")

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
            outer = json.loads(msg.value.decode("utf-8"))
            gap = outer.get("payload", {})
            if not gap:
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
            await producer.send_and_wait(output_topic, json.dumps({"payload": replay}).encode("utf-8"))
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
