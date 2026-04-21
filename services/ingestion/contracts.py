import json
import uuid
from datetime import datetime, timezone

from psycopg import Connection


def build_envelope(payload: dict, schema_version: int = 1, message_id: str | None = None) -> dict:
    return {
        "message_id": message_id or str(uuid.uuid4()),
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": schema_version,
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


def parse_json_bytes(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))
