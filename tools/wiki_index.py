#!/usr/bin/env python3
from pathlib import Path

wiki = Path("wiki")
sections: dict[str, list[tuple[str, str]]] = {}

for p in sorted(wiki.rglob("*.md")):
    if p.name == "index.md":
        continue
    rel = p.relative_to(wiki)
    folder = rel.parts[0] if len(rel.parts) > 1 else "root"

    title = p.stem.replace("-", " ").title()
    text = p.read_text(encoding="utf-8")
    first_h1 = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), "")
    if first_h1:
        title = first_h1

    sections.setdefault(folder, []).append((rel.as_posix(), title))

out = ["---", "type: index", "status: active", "---", "", "# Index", ""]
for folder in sorted(sections):
    out += [f"## {folder.title()}", ""]
    out += [f"- [[{rel[:-3]}|{title}]]" for rel, title in sections[folder]]
    out += [""]

(wiki / "index.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("Updated wiki/index.md")
