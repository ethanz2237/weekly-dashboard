def test_cli_imports_successfully():
    import dashboard.run

    assert dashboard.run.VALID_MODES == ("build", "validate-sources", "publish-notion", "check-env", "source-health", "pre-notion-check")


def test_check_env_masks_credentials(monkeypatch, capsys):
    import dashboard.run

    monkeypatch.setenv("FRED_API_KEY", "1234567890abcdef")
    monkeypatch.setenv("NOTION_TOKEN", "secret_notion_token")
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    dashboard.run.check_env()
    output = capsys.readouterr().out

    assert "1234...cdef" in output
    assert "secr...oken" in output
    assert "secret_notion_token" not in output
    assert "NOTION_DATABASE_ID: missing" in output
