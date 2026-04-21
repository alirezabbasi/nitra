import asyncio
import json
import os
from datetime import datetime, timezone

import psycopg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def minute_bucket(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0, tzinfo=timezone.utc)


async def main() -> None:
    brokers = env("KAFKA_BROKERS", "kafka:9092")
    input_topic = env("BAR_INPUT_TOPIC", "normalized.quote.fx")
    output_topic = env("BAR_OUTPUT_TOPIC", "bar.1m")
    group_id = env("BAR_GROUP_ID", "nitra-bar-aggregation-v1")
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
    state: dict[tuple[str, str], dict] = {}

    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            outer = json.loads(msg.value.decode("utf-8"))
            event = outer.get("payload", {})
            if not event:
                await consumer.commit()
                continue

            venue = event.get("venue")
            symbol = event.get("canonical_symbol")
            mid = event.get("mid")
            if not venue or not symbol or mid is None:
                await consumer.commit()
                continue

            event_ts = parse_ts(event.get("event_ts_exchange", datetime.now(timezone.utc).isoformat()))
            bucket = minute_bucket(event_ts)
            key = (venue, symbol)
            value = float(mid)
            current = state.get(key)

            if current and current["bucket_start"] != bucket:
                flush = current
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ohlcv_bar (
                          venue, canonical_symbol, timeframe, bucket_start,
                          open, high, low, close, volume, trade_count, last_event_ts
                        ) VALUES (%s,%s,'1m',%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (venue, canonical_symbol, timeframe, bucket_start)
                        DO UPDATE SET
                          high = GREATEST(ohlcv_bar.high, EXCLUDED.high),
                          low = LEAST(ohlcv_bar.low, EXCLUDED.low),
                          close = EXCLUDED.close,
                          trade_count = GREATEST(COALESCE(ohlcv_bar.trade_count,0), COALESCE(EXCLUDED.trade_count,0)),
                          last_event_ts = GREATEST(ohlcv_bar.last_event_ts, EXCLUDED.last_event_ts),
                          updated_at = now()
                        """,
                        (
                            flush["venue"],
                            flush["canonical_symbol"],
                            flush["bucket_start"],
                            flush["open"],
                            flush["high"],
                            flush["low"],
                            flush["close"],
                            None,
                            flush["trade_count"],
                            flush["last_event_ts"],
                        ),
                    )
                conn.commit()
                bar_event = {
                    "venue": flush["venue"],
                    "canonical_symbol": flush["canonical_symbol"],
                    "timeframe": "1m",
                    "bucket_start": flush["bucket_start"].isoformat(),
                    "open": flush["open"],
                    "high": flush["high"],
                    "low": flush["low"],
                    "close": flush["close"],
                    "trade_count": flush["trade_count"],
                    "last_event_ts": flush["last_event_ts"].isoformat(),
                }
                await producer.send_and_wait(output_topic, json.dumps({"payload": bar_event}).encode("utf-8"))

            if not current or current["bucket_start"] != bucket:
                state[key] = {
                    "venue": venue,
                    "canonical_symbol": symbol,
                    "bucket_start": bucket,
                    "open": value,
                    "high": value,
                    "low": value,
                    "close": value,
                    "trade_count": 1,
                    "last_event_ts": event_ts,
                }
            else:
                current["high"] = max(current["high"], value)
                current["low"] = min(current["low"], value)
                current["close"] = value
                current["trade_count"] += 1
                current["last_event_ts"] = event_ts

            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
