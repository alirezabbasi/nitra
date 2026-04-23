import asyncio
import json
import os
import random
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer

from ingestion.contracts import build_envelope


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def csv_env(name: str, default: str) -> list[str]:
    raw = env(name, default)
    values = [item.strip() for item in raw.split(",")]
    return [item for item in values if item]


def compact_symbol(symbol: str) -> str:
    upper = symbol.strip().upper()
    return "".join(ch for ch in upper if ch.isalnum())


def compact_capital_symbol(symbol: str) -> str:
    upper = symbol.strip().upper()
    prefix = "CS.D."
    suffix = ".MINI.IP"
    if upper.startswith(prefix) and upper.endswith(suffix):
        core = upper[len(prefix) : -len(suffix)]
        if len(core) == 6 and core.isalpha():
            return core
    return compact_symbol(upper)


def compact_symbol_for_venue(venue: str, symbol: str) -> str:
    if venue.lower() == "capital":
        return compact_capital_symbol(symbol)
    return compact_symbol(symbol)


async def main() -> None:
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    raw_topic = env("INGESTION_RAW_TOPIC", "raw.market.oanda")
    health_topic = env("INGESTION_HEALTH_TOPIC", "connector.health")
    venue = env("INGESTION_VENUE", "oanda")
    default_symbol = env("INGESTION_SYMBOL", "EURUSD")
    symbols = csv_env("INGESTION_ENABLED_INSTRUMENTS", default_symbol)
    output_symbols = [compact_symbol_for_venue(venue, s) for s in symbols]
    interval_secs = float(env("INGESTION_INTERVAL_SECS", "1.0"))
    connector_mode = env("CONNECTOR_MODE", "mock")

    producer = AIOKafkaProducer(bootstrap_servers=brokers)
    await producer.start()

    price = 1.0850
    try:
        while True:
            price += random.uniform(-0.0002, 0.0002)
            bid = round(price - 0.00005, 6)
            ask = round(price + 0.00005, 6)
            mid = round((bid + ask) / 2, 6)

            for source_symbol, output_symbol in zip(symbols, output_symbols):
                raw_payload = {
                    "venue": venue,
                    "broker_symbol": output_symbol,
                    "event_ts_received": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "bid": bid,
                        "ask": ask,
                        "mid": mid,
                        "sequence_id": str(uuid.uuid4()),
                        "source_symbol": source_symbol,
                    },
                    "source": "nitra.market_ingestion.mock",
                }
                health_payload = {
                    "service": "market-ingestion",
                    "status": "ok",
                    "mode": connector_mode,
                    "venue": venue,
                    "symbol": output_symbol,
                    "source_symbol": source_symbol,
                    "enabled_instruments": output_symbols,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }

                await producer.send_and_wait(raw_topic, json.dumps(build_envelope(raw_payload)).encode("utf-8"))
                await producer.send_and_wait(health_topic, json.dumps(build_envelope(health_payload)).encode("utf-8"))
            await asyncio.sleep(interval_secs)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
