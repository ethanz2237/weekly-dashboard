from pathlib import Path

from dashboard.publish.notion import markdown_to_blocks, publish_dashboard


class _Response:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {"id": "page-id", "url": "https://notion.so/page-id"}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("request failed with token secret_notion_token")

    def json(self):
        return self.payload


class _Session:
    def __init__(self, response=None):
        self.response = response or _Response()
        self.calls = []

    def post(self, url, headers=None, json=None, files=None, timeout=None):
        self.calls.append({"method": "post", "url": url, "headers": headers, "json": json, "files": files, "timeout": timeout})
        if url.endswith("/file_uploads"):
            return _Response({"id": "upload-id"})
        return self.response

    def patch(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"method": "patch", "url": url, "headers": headers, "json": json, "timeout": timeout})
        return _Response({})


def test_publish_dashboard_creates_page_in_existing_data_source(tmp_path, monkeypatch):
    output = tmp_path / "output"
    (output / "charts").mkdir(parents=True)
    (output / "charts" / "example.png").write_bytes(b"png")
    (output / "dashboard.md").write_text("# Weekly Financial Dashboard\n\n![Chart](charts/example.png)\n")
    (output / "dashboard.json").write_text('{"executive_snapshot": {"data_as_of_date": "2026-07-03"}}')
    monkeypatch.setenv("NOTION_TOKEN", "secret_notion_token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "database-id")
    monkeypatch.setenv("NOTION_DATA_SOURCE_ID", "data-source-id")
    session = _Session()

    result = publish_dashboard("latest", output, session)

    assert result.success is True
    body = session.calls[0]["json"]
    assert body["parent"] == {"type": "data_source_id", "data_source_id": "data-source-id"}
    assert body["properties"]["Name"]["title"][0]["text"]["content"] == "Weekly Market Dashboard - 2026-07-03"
    assert body["properties"]["Tags"]["multi_select"] == [
        {"name": "US"},
        {"name": "Europe"},
        {"name": "China"},
        {"name": "Japan"},
        {"name": "EM"},
    ]
    appended = next(call["json"]["children"] for call in session.calls if call["method"] == "patch")
    assert any(block["type"] == "image" and block["image"]["file_upload"]["id"] == "upload-id" for block in appended)
    assert session.calls[0]["headers"]["Authorization"] == "Bearer secret_notion_token"


def test_publish_dashboard_missing_credentials_is_graceful(tmp_path, monkeypatch):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.setenv("NOTION_DATABASE_ID", "database-id")

    result = publish_dashboard(output_root=tmp_path)

    assert result.success is False
    assert "NOTION_TOKEN" in result.message


def test_publish_dashboard_sanitizes_failed_request(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    (output / "dashboard.md").write_text("# Dashboard\n")
    monkeypatch.setenv("NOTION_TOKEN", "secret_notion_token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "database-id")

    result = publish_dashboard(output_root=output, session=_Session(_Response(status_code=400)))

    assert result.success is False
    assert "secret_notion_token" not in result.message
    assert "***" in result.message


def test_publish_dashboard_uses_latest_dashboard_path(tmp_path, monkeypatch):
    output = tmp_path / "output"
    latest = output / "latest"
    latest.mkdir(parents=True)
    (latest / "dashboard.md").write_text("# Latest Dashboard\n")
    (latest / "dashboard.json").write_text('{"executive_snapshot": {"data_as_of_date": "2026-07-04"}}')
    monkeypatch.setenv("NOTION_TOKEN", "secret_notion_token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "database-id")
    monkeypatch.delenv("NOTION_DATA_SOURCE_ID", raising=False)
    session = _Session()

    result = publish_dashboard(output_root=output, session=session)

    assert result.success is True
    assert session.calls[0]["json"]["parent"] == {"type": "database_id", "database_id": "database-id"}
    assert session.calls[0]["json"]["properties"]["Name"]["title"][0]["text"]["content"].endswith("2026-07-04")


def test_markdown_to_blocks_converts_pipe_tables_to_notion_tables():
    blocks = markdown_to_blocks("# Title\n| a | b |\n| --- | --- |\n| 1 | 2 |\n")

    assert blocks[0]["type"] == "heading_1"
    assert blocks[1]["type"] == "table"
    assert blocks[1]["table"]["children"][0]["type"] == "table_row"
    assert all(block["type"] != "code" for block in blocks)


def test_png_chart_upload_creates_image_block(tmp_path):
    chart = tmp_path / "charts" / "example.png"
    chart.parent.mkdir()
    chart.write_bytes(b"png")
    session = _Session()

    blocks = markdown_to_blocks("![Chart](charts/example.png)", tmp_path, session, "secret")

    assert blocks[0]["type"] == "image"
    assert blocks[0]["image"]["file_upload"]["id"] == "upload-id"


class _FailingUploadSession(_Session):
    def post(self, url, headers=None, json=None, files=None, timeout=None):
        if url.endswith("/file_uploads"):
            raise RuntimeError("upload failed")
        return super().post(url, headers=headers, json=json, files=files, timeout=timeout)


def test_chart_upload_failure_falls_back_gracefully(tmp_path):
    chart = tmp_path / "charts" / "example.png"
    chart.parent.mkdir()
    chart.write_bytes(b"png")

    blocks = markdown_to_blocks("![Chart](charts/example.png)", tmp_path, _FailingUploadSession(), "secret")

    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "Chart upload failed: charts/example.png"
    assert "Chart placeholder" not in blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
