import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import psycopg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def parse_ts(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def canonical_symbol(broker_symbol: str) -> str:
    return broker_symbol.replace("_", "").replace("-", "").replace(".", "").upper()


def envelope(payload: dict, schema_version: int = 1) -> dict:
    return {
        "message_id": str(uuid.uuid4()),
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": schema_version,
        "headers": {},
        "payload": payload,
        "retry": None,
    }


def classify(payload: dict) -> str:
    if payload.get("bid") is not None or payload.get("ask") is not None:
        return "raw_tick"
    if payload.get("price") is not None and payload.get("size") is not None:
        return "trade_print"
    if payload.get("best_bid") is not None or payload.get("best_ask") is not None:
        return "book_event"
    return "raw_tick"


def persist_market_entity(conn: psycopg.Connection, entity_type: str, message_id: str, raw_event: dict) -> None:
    venue = raw_event["venue"]
    broker_symbol = raw_event["broker_symbol"]
    event_ts_received = parse_ts(raw_event.get("event_ts_received"))
    source = raw_event.get("source", "nitra.market_normalization")
    payload = raw_event.get("payload", {})
    sequence_id = payload.get("sequence_id")
    event_ts_exchange = parse_ts(payload.get("event_ts_exchange")) if payload.get("event_ts_exchange") else None

    with conn.cursor() as cur:
        if entity_type == "trade_print":
            cur.execute(
                """
                INSERT INTO trade_print (
                  message_id, venue, broker_symbol, event_ts_exchange, event_ts_received,
                  source, price, size, side, sequence_id, payload
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (message_id, event_ts_received) DO NOTHING
                """,
                (
                    message_id,
                    venue,
                    broker_symbol,
                    event_ts_exchange,
                    event_ts_received,
                    source,
                    payload.get("price"),
                    payload.get("size"),
                    payload.get("side"),
                    sequence_id,
                    json.dumps(payload),
                ),
            )
        elif entity_type == "book_event":
            cur.execute(
                """
                INSERT INTO book_event (
                  message_id, venue, broker_symbol, event_ts_exchange, event_ts_received,
                  source, best_bid, best_ask, sequence_id, payload
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (message_id, event_ts_received) DO NOTHING
                """,
                (
                    message_id,
                    venue,
                    broker_symbol,
                    event_ts_exchange,
                    event_ts_received,
                    source,
                    payload.get("best_bid"),
                    payload.get("best_ask"),
                    sequence_id,
                    json.dumps(payload),
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO raw_tick (
                  message_id, venue, broker_symbol, event_ts_exchange, event_ts_received,
                  source, bid, ask, mid, last, sequence_id, payload
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (message_id, event_ts_received) DO NOTHING
                """,
                (
                    message_id,
                    venue,
                    broker_symbol,
                    event_ts_exchange,
                    event_ts_received,
                    source,
                    payload.get("bid"),
                    payload.get("ask"),
                    payload.get("mid"),
                    payload.get("last"),
                    sequence_id,
                    json.dumps(payload),
                ),
            )
    conn.commit()


async def main() -> None:
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    input_topics = env("NORMALIZER_INPUT_TOPICS", "raw.market.oanda,raw.market.capital,raw.market.coinbase").split(",")
    output_topic = env("NORMALIZER_OUTPUT_TOPIC", "normalized.quote.fx")
    group_id = env("NORMALIZER_GROUP_ID", "nitra-market-normalization-v1")
    db_dsn = env("DATABASE_URL", "postgresql://trading:trading@timescaledb:5432/trading")

    conn = psycopg.connect(db_dsn)
    consumer = AIOKafkaConsumer(
        *[t.strip() for t in input_topics if t.strip()],
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
            message_id = outer.get("message_id", str(uuid.uuid4()))
            raw_event = outer.get("payload", {})
            if not raw_event:
                await consumer.commit()
                continue

            entity_type = classify(raw_event.get("payload", {}))
            persist_market_entity(conn, entity_type, message_id, raw_event)

            payload = raw_event.get("payload", {})
            bid = payload.get("bid")
            ask = payload.get("ask")
            mid = payload.get("mid")
            if mid is None and bid is not None and ask is not None:
                mid = (float(bid) + float(ask)) / 2.0

            normalized = {
                "event_id": str(uuid.uuid4()),
                "venue": raw_event.get("venue", "unknown"),
                "asset_class": "fx",
                "broker_symbol": raw_event.get("broker_symbol", "UNKNOWN"),
                "canonical_symbol": canonical_symbol(raw_event.get("broker_symbol", "UNKNOWN")),
                "event_type": "quote",
                "event_ts_exchange": payload.get("event_ts_exchange", datetime.now(timezone.utc).isoformat()),
                "event_ts_received": raw_event.get("event_ts_received", datetime.now(timezone.utc).isoformat()),
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "last": payload.get("last"),
                "volume": payload.get("size"),
                "sequence_id": payload.get("sequence_id"),
                "source_checksum": "n/a",
                "ingestion_run_id": "dev-local",
                "schema_version": 1,
            }

            await producer.send_and_wait(output_topic, json.dumps(envelope(normalized)).encode("utf-8"))
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
