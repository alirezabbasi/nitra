import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import psycopg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from psycopg import Connection

from ingestion.contracts import build_envelope, is_message_processed, parse_json_bytes, record_message_processed
from ingestion.domain import (
    canonical_symbol,
    classify_market_payload,
    infer_asset_class_from_symbol,
    load_symbol_registry,
    parse_ts,
)


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def persist_market_entity(conn: Connection, entity_type: str, message_id: str, raw_event: dict) -> None:
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
                ) VALUES (%s::uuid,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
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
                ) VALUES (%s::uuid,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
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
                ) VALUES (%s::uuid,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
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


def canonical_from_registry_or_fallback(registry: dict[tuple[str, str], str], venue: str, broker_symbol: str) -> str:
    return registry.get((venue.lower(), broker_symbol), canonical_symbol(broker_symbol))


async def main() -> None:
    service_name = "market_normalization"
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    input_topics = env("NORMALIZER_INPUT_TOPICS", "raw.market.oanda,raw.market.capital,raw.market.coinbase").split(",")
    output_topic = env("NORMALIZER_OUTPUT_TOPIC", "normalized.quote.fx")
    group_id = env("NORMALIZER_GROUP_ID", "nitra-market-normalization-v1")
    db_dsn = env("DATABASE_URL", "postgresql://trading:trading@timescaledb:5432/trading")
    registry_path = env("NORMALIZER_SYMBOL_REGISTRY_PATH", "/app/ingestion/registry.v1.json")

    registry = load_symbol_registry(registry_path)
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
            source_topic = msg.topic
            source_partition = msg.partition
            source_offset = msg.offset

            outer = parse_json_bytes(msg.value)
            message_id = outer.get("message_id") or str(uuid.uuid4())
            raw_event = outer.get("payload", {})
            if not raw_event:
                await consumer.commit()
                continue

            if is_message_processed(conn, service_name, message_id):
                await consumer.commit()
                continue

            entity_type = classify_market_payload(raw_event.get("payload", {}))
            persist_market_entity(conn, entity_type, message_id, raw_event)

            payload = raw_event.get("payload", {})
            bid = payload.get("bid")
            ask = payload.get("ask")
            mid = payload.get("mid")
            if mid is None and bid is not None and ask is not None:
                mid = (float(bid) + float(ask)) / 2.0

            broker_symbol = raw_event.get("broker_symbol", "UNKNOWN")
            venue = raw_event.get("venue", "unknown")
            canonical = canonical_from_registry_or_fallback(registry, venue, broker_symbol)
            normalized = {
                "event_id": str(uuid.uuid4()),
                "venue": venue,
                "asset_class": infer_asset_class_from_symbol(canonical),
                "broker_symbol": broker_symbol,
                "canonical_symbol": canonical,
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

            await producer.send_and_wait(output_topic, json.dumps(build_envelope(normalized)).encode("utf-8"))
            record_message_processed(
                conn,
                service_name,
                message_id,
                source_topic,
                source_partition,
                source_offset,
            )
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
