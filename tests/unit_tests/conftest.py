import pytest


@pytest.fixture
def github_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_API_TOKEN", "token")


@pytest.fixture
def missing_github_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITHUB_API_TOKEN", raising=False)


@pytest.fixture
def conbench_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONBENCH_URL", "https://conbench.biz")
    monkeypatch.setenv("CONBENCH_EMAIL", "email")
    monkeypatch.setenv("CONBENCH_PASSWORD", "password")


@pytest.fixture
def missing_conbench_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CONBENCH_URL", raising=False)
    monkeypatch.delenv("CONBENCH_EMAIL", raising=False)
    monkeypatch.delenv("CONBENCH_PASSWORD", raising=False)
