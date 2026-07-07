"""Publish the generated dashboard to an existing Notion data source."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import requests

from dashboard.config import ROOT
from dashboard.utils.sanitize import sanitize


NOTION_PAGES_URL = "https://api.notion.com/v1/pages"
NOTION_FILE_UPLOADS_URL = "https://api.notion.com/v1/file_uploads"
NOTION_BLOCKS_URL = "https://api.notion.com/v1/blocks"
NOTION_VERSION = "2026-03-11"
DEFAULT_TAGS = ["US", "Europe", "China", "Japan", "EM"]
AUTOFILL_TEXT = "Automated weekly cross-asset macro dashboard generated from Python."


@dataclass(frozen=True)
class PublishResult:
    success: bool
    message: str
    page_id: str | None = None
    url: str | None = None


def publish_dashboard(
    as_of: str = "latest",
    output_root: Path = ROOT / "output",
    session: requests.Session | None = None,
) -> PublishResult:
    token = os.getenv("NOTION_TOKEN", "")
    database_id = os.getenv("NOTION_DATABASE_ID", "")
    data_source_id = os.getenv("NOTION_DATA_SOURCE_ID", "")
    if not token or not database_id:
        missing = ", ".join(name for name, value in [("NOTION_TOKEN", token), ("NOTION_DATABASE_ID", database_id)] if not value)
        return PublishResult(False, f"Missing Notion credential(s): {missing}")

    markdown_path = _dashboard_markdown_path(output_root)
    if markdown_path is None:
        return PublishResult(False, f"Dashboard markdown not found under {output_root}")

    layout = _read_layout(markdown_path)
    as_of_date = _as_of_date(layout, as_of)
    body = {
        "parent": _parent(database_id, data_source_id),
        "properties": _properties(as_of_date),
    }
    client = session or requests.Session()
    try:
        response = client.post(NOTION_PAGES_URL, headers=_headers(token), json=body, timeout=30)
        response.raise_for_status()
        payload = response.json()
        page_id = payload.get("id")
        if page_id:
            blocks = markdown_to_blocks(markdown_path.read_text(), markdown_path.parent, client, token)
            _append_blocks(client, token, page_id, blocks)
    except Exception as exc:
        return PublishResult(False, f"Notion publish failed: {sanitize(exc)}")

    return PublishResult(True, "Published dashboard to Notion.", payload.get("id"), payload.get("url"))


def markdown_to_blocks(
    markdown: str,
    markdown_parent: Path | None = None,
    session: requests.Session | None = None,
    token: str = "",
    max_blocks: int = 90,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    table_lines: list[str] = []

    def flush_table() -> None:
        if table_lines:
            blocks.extend(_table_blocks(table_lines))
            table_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("|"):
            table_lines.append(line)
            continue
        flush_table()
        if not line:
            continue
        block = _line_to_block(line, markdown_parent, session, token)
        if block:
            blocks.append(block)
        if len(blocks) >= max_blocks:
            blocks.append(_paragraph("Dashboard truncated for Notion block limit. See output/dashboard.md for the full generated file."))
            return blocks[: max_blocks + 1]

    flush_table()
    return blocks[:max_blocks] or [_paragraph("Dashboard content was empty.")]


def _dashboard_markdown_path(output_root: Path) -> Path | None:
    for path in (output_root / "latest" / "dashboard.md", output_root / "dashboard.md"):
        if path.exists():
            return path
    return None


def _read_layout(markdown_path: Path) -> dict[str, Any]:
    for path in (markdown_path.with_suffix(".json"), markdown_path.parent / "dashboard.json"):
        if path.exists():
            return json.loads(path.read_text())
    return {}


def _as_of_date(layout: dict[str, Any], requested: str) -> str:
    snapshot = layout.get("executive_snapshot", {})
    if requested != "latest":
        return requested
    return snapshot.get("data_as_of_date") or snapshot.get("requested_as_of") or date.today().isoformat()


def _parent(database_id: str, data_source_id: str) -> dict[str, str]:
    if data_source_id:
        return {"type": "data_source_id", "data_source_id": data_source_id}
    return {"type": "database_id", "database_id": database_id}


def _properties(as_of_date: str) -> dict[str, Any]:
    return {
        "Name": {"title": [{"text": {"content": f"Weekly Market Dashboard - {as_of_date}"}}]},
        "Published": {"date": {"start": date.today().isoformat()}},
        "Tags": {"multi_select": [{"name": tag} for tag in DEFAULT_TAGS]},
        "AI custom autofill": {"rich_text": [{"text": {"content": AUTOFILL_TEXT}}]},
    }


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _append_blocks(client: requests.Session, token: str, page_id: str, blocks: list[dict[str, Any]]) -> None:
    for i in range(0, len(blocks), 90):
        response = client.patch(f"{NOTION_BLOCKS_URL}/{page_id}/children", headers=_headers(token), json={"children": blocks[i : i + 90]}, timeout=30)
        response.raise_for_status()


def _line_to_block(line: str, markdown_parent: Path | None = None, session: requests.Session | None = None, token: str = "") -> dict[str, Any] | None:
    if line.startswith("# "):
        return _text_block("heading_1", line[2:])
    if line.startswith("## "):
        return _text_block("heading_2", line[3:])
    if line.startswith("### "):
        return _text_block("heading_3", line[4:])
    if line.startswith("- "):
        return _text_block("bulleted_list_item", line[2:])
    if line.startswith("!["):
        return _image_block(_image_label(line), markdown_parent, session, token)
    return _paragraph(line)


def _image_block(path_text: str, markdown_parent: Path | None, session: requests.Session | None, token: str) -> dict[str, Any]:
    if not markdown_parent or not session or not token:
        return _paragraph(f"Chart upload failed: {path_text}")
    path = (markdown_parent / path_text).resolve()
    try:
        upload_id = _upload_file(session, token, path)
        return {
            "type": "image",
            "image": {"type": "file_upload", "file_upload": {"id": upload_id}},
        }
    except Exception:
        return _paragraph(f"Chart upload failed: {path_text}")


def _upload_file(session: requests.Session, token: str, path: Path) -> str:
    response = session.post(
        NOTION_FILE_UPLOADS_URL,
        headers=_headers(token),
        json={"mode": "single_part", "filename": path.name, "content_type": "image/png"},
        timeout=30,
    )
    response.raise_for_status()
    upload_id = response.json()["id"]
    with path.open("rb") as file:
        response = session.post(
            f"{NOTION_FILE_UPLOADS_URL}/{upload_id}/send",
            headers={key: value for key, value in _headers(token).items() if key != "Content-Type"},
            files={"file": (path.name, file, "image/png")},
            timeout=60,
        )
    response.raise_for_status()
    return upload_id


def _table_blocks(lines: list[str], max_rows: int = 80) -> list[dict[str, Any]]:
    rows = [_split_table_row(line) for line in lines if line.startswith("|")]
    rows = [row for row in rows if row and not all(set(cell) <= {"-"} for cell in row)]
    if not rows:
        return []
    width = max(len(row) for row in rows)
    truncated = len(rows) > max_rows
    rows = rows[:max_rows]
    block = {
        "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": True,
            "has_row_header": False,
            "children": [
                {"type": "table_row", "table_row": {"cells": [_rich_text(cell) for cell in row + [""] * (width - len(row))]}}
                for row in rows
            ],
        },
    }
    return [block, _paragraph("Table rows were truncated for Notion limits.")] if truncated else [block]


def _split_table_row(line: str) -> list[str]:
    return [cell.strip().replace("\\|", "|") for cell in line.strip().strip("|").split("|")]


def _text_block(kind: str, text: str) -> dict[str, Any]:
    return {kind: {"rich_text": _rich_text(text)}, "type": kind}


def _paragraph(text: str) -> dict[str, Any]:
    return _text_block("paragraph", text)


def _rich_text(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": chunk}} for chunk in _chunks(text, 1900)]


def _chunks(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _image_label(line: str) -> str:
    if "](" in line and line.endswith(")"):
        return line.rsplit("](", 1)[1][:-1]
    return line
