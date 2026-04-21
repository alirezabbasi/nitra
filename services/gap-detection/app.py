import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def main() -> None:
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    input_topic = env("GAP_INPUT_TOPIC", "bar.1m")
    output_topic = env("GAP_OUTPUT_TOPIC", "gap.events")
    group_id = env("GAP_GROUP_ID", "nitra-gap-detection-v1")

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
            outer = json.loads(msg.value.decode("utf-8"))
            bar = outer.get("payload", {})
            venue = bar.get("venue")
            symbol = bar.get("canonical_symbol")
            bucket_raw = bar.get("bucket_start")
            if not venue or not symbol or not bucket_raw:
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
                await producer.send_and_wait(output_topic, json.dumps({"payload": gap_event}).encode("utf-8"))
            last_bucket[key] = bucket
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
