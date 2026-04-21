import asyncio
import json
import os
import random
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def envelope(payload: dict, schema_version: int = 1) -> dict:
    return {
        "message_id": str(uuid.uuid4()),
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": schema_version,
        "headers": {},
        "payload": payload,
        "retry": None,
    }


async def main() -> None:
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    raw_topic = env("INGESTION_RAW_TOPIC", "raw.market.oanda")
    health_topic = env("INGESTION_HEALTH_TOPIC", "connector.health")
    venue = env("INGESTION_VENUE", "oanda")
    symbol = env("INGESTION_SYMBOL", "EUR_USD")
    interval_secs = float(env("INGESTION_INTERVAL_SECS", "1.0"))

    producer = AIOKafkaProducer(bootstrap_servers=brokers)
    await producer.start()

    price = 1.0850
    try:
        while True:
            price += random.uniform(-0.0002, 0.0002)
            bid = round(price - 0.00005, 6)
            ask = round(price + 0.00005, 6)
            mid = round((bid + ask) / 2, 6)

            raw_payload = {
                "venue": venue,
                "broker_symbol": symbol,
                "event_ts_received": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "bid": bid,
                    "ask": ask,
                    "mid": mid,
                    "sequence_id": str(uuid.uuid4()),
                },
                "source": "nitra.market_ingestion.mock",
            }
            health_payload = {
                "service": "market-ingestion",
                "status": "ok",
                "venue": venue,
                "symbol": symbol,
                "ts": datetime.now(timezone.utc).isoformat(),
            }

            await producer.send_and_wait(raw_topic, json.dumps(envelope(raw_payload)).encode("utf-8"))
            await producer.send_and_wait(health_topic, json.dumps(envelope(health_payload)).encode("utf-8"))
            await asyncio.sleep(interval_secs)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
