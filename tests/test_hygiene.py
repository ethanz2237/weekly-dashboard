from pathlib import Path


def test_gitignore_excludes_local_env_and_venv():
    gitignore = Path(".gitignore").read_text().splitlines()

    assert ".env" in gitignore
    assert ".venv/" in gitignore
