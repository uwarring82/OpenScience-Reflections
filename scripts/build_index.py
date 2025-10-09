#!/usr/bin/env python3
"""Build the reflections index and ensure reflection metadata integrity."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover - dependency error is explicit for contributors
    raise SystemExit("PyYAML is required. Install it with `pip install pyyaml`.") from exc

ROOT = Path(__file__).resolve().parents[1]
REFLECTIONS_DIR = ROOT / "reflections"
INDEX_PATH = REFLECTIONS_DIR / "index.json"
HASH_LENGTH = 12
FRONTMATTER_ORDER = ["id", "author", "tags", "summary", "status"]


def split_front_matter(text: str) -> Tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("Reflection files must start with YAML front matter delimited by ---")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("Missing closing --- delimiter in front matter")
    fm_text = text[4:end]
    remainder = text[end + 4 :]
    if remainder.startswith("\n"):
        remainder = remainder[1:]
    return fm_text, remainder


def load_front_matter(fm_text: str) -> Dict[str, Any]:
    data = yaml.safe_load(fm_text) or {}
    if not isinstance(data, dict):
        raise ValueError("Front matter must parse to a mapping")
    return data


def dump_front_matter(data: Dict[str, Any]) -> str:
    ordered: Dict[str, Any] = {}
    for key in FRONTMATTER_ORDER:
        if key in data:
            ordered[key] = data[key]
    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value
    return yaml.safe_dump(ordered, sort_keys=False).strip()


def compute_reflection_id(relative_path: str, body: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(relative_path.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(body.encode("utf-8"))
    return hasher.hexdigest()[:HASH_LENGTH]


def extract_title(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def process_reflection(path: Path, write: bool = True) -> Tuple[Dict[str, Any], bool]:
    text = path.read_text(encoding="utf-8")
    fm_text, body = split_front_matter(text)
    front_matter = load_front_matter(fm_text)

    relative_path = path.relative_to(ROOT).as_posix()
    body_clean = body.lstrip("\n")
    body_normalised = body_clean.rstrip() + "\n" if body_clean else ""

    reflection_id = front_matter.get("id", "provisional")
    if reflection_id in {None, "", "provisional"}:
        reflection_id = compute_reflection_id(relative_path, body_normalised)
        front_matter["id"] = reflection_id

    fm_dump = dump_front_matter(front_matter)
    new_text = f"---\n{fm_dump}\n---\n\n{body_normalised}" if body_normalised else f"---\n{fm_dump}\n---\n"
    changed = text != new_text
    if changed and write:
        path.write_text(new_text, encoding="utf-8")

    metadata = {
        "id": front_matter.get("id"),
        "path": relative_path,
        "author": front_matter.get("author"),
        "tags": front_matter.get("tags", []),
        "summary": front_matter.get("summary", ""),
        "status": front_matter.get("status", ""),
        "title": extract_title(body),
        "updated_at": dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    return metadata, changed


def build_index(write: bool = True) -> Tuple[Dict[str, Any], List[str], str]:
    entries: List[Dict[str, Any]] = []
    modified: List[str] = []

    if REFLECTIONS_DIR.exists():
        reflection_paths = sorted(REFLECTIONS_DIR.rglob("*.md"))
        for path in reflection_paths:
            metadata, changed = process_reflection(path, write=write)
            entries.append(metadata)
            if changed:
                modified.append(path.relative_to(ROOT).as_posix())

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing_content = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else None
    existing_data = None
    if existing_content:
        try:
            existing_data = json.loads(existing_content)
        except json.JSONDecodeError:
            existing_data = None

    generated_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    if not write and existing_data and isinstance(existing_data, dict) and "generated_at" in existing_data:
        generated_at = existing_data["generated_at"]

    index_data = {
        "schema": "reflection_v1",
        "generated_at": generated_at,
        "count": len(entries),
        "reflections": entries,
    }
    index_content = json.dumps(index_data, indent=2, ensure_ascii=False) + "\n"

    if write:
        INDEX_PATH.write_text(index_content, encoding="utf-8")
    else:
        if existing_content != index_content:
            modified.append(INDEX_PATH.relative_to(ROOT).as_posix())

    return index_data, modified, index_content


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the reflections index.")
    parser.add_argument("--check", action="store_true", help="Exit with 1 if running the builder would modify files.")
    args = parser.parse_args(argv)

    if args.check:
        _, modified, _ = build_index(write=False)
        if modified:
            sys.stderr.write("The following files would be modified: " + ", ".join(modified) + "\n")
            return 1
    else:
        build_index(write=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
