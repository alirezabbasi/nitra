#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOPICS = ROOT / "infra/kafka/topics.csv"
CURRENT_DIR = ROOT / "infra/kafka/schemas/current"
BASELINE_DIR = ROOT / "infra/kafka/schemas/baseline"


def fail(msg: str) -> None:
    print(f"[schema-compat] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid json {path}: {exc}")
    raise AssertionError("unreachable")


def check_compat(old: dict, new: dict, topic: str) -> None:
    if old.get("type") != "object" or new.get("type") != "object":
        fail(f"{topic}: schemas must be type=object")
    old_props = old.get("properties", {})
    new_props = new.get("properties", {})
    for key, old_def in old_props.items():
        if key not in new_props:
            fail(f"{topic}: missing property in current schema: {key}")
        if old_def.get("type") != new_props[key].get("type"):
            fail(f"{topic}: property type changed for {key}")
    old_req = set(old.get("required", []))
    new_req = set(new.get("required", []))
    if not new_req.issubset(old_req):
        added = sorted(new_req - old_req)
        fail(f"{topic}: backward incompatible required additions: {added}")
    if not old_req.issubset(new_req):
        removed = sorted(old_req - new_req)
        fail(f"{topic}: forward incompatible required removals: {removed}")


def main() -> int:
    if not TOPICS.exists():
        fail(f"missing topics catalog: {TOPICS}")
    rows: list[str] = []
    with TOPICS.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for raw in reader:
            if not raw:
                continue
            topic = raw[0].strip()
            if not topic or topic.startswith("#"):
                continue
            rows.append(topic)

    if not rows:
        fail("no runtime topics found")

    checked = 0
    for topic in rows:
        current = CURRENT_DIR / f"{topic}.schema.json"
        baseline = BASELINE_DIR / f"{topic}.schema.json"
        if not current.exists():
            fail(f"{topic}: missing current schema {current}")
        if not baseline.exists():
            fail(f"{topic}: missing baseline schema {baseline}")
        old = load_json(baseline)
        new = load_json(current)
        check_compat(old, new, topic)
        checked += 1

    print(f"[schema-compat] PASS topics_checked={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
