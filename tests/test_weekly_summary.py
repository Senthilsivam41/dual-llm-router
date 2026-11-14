"""Weekly summary text and optional Slack/Discord delivery."""

import http.client
import json
import logging
import re
import sys
from pathlib import Path
from unittest.mock import patch

from evals.alerts import post_json_webhook
from evals.summary_webhook import (
    message_payload,
    notify_weekly_summary,
    weekly_summary_markdown,
)
from scripts.weekly_summary import main

ROOT = Path(__file__).resolve().parents[1]


def test_summary_uses_success_and_winner(tmp_path):
    (tmp_path / "full_easy.json").write_text(
        json.dumps({"overall": {"success_rate": 1.0, "avg_quality": 0.5}}),
        encoding="utf-8",
    )
    (tmp_path / "comparative.json").write_text(
        json.dumps({"winner": "hermes_v1,laguna_v1", "ranking": ["hermes_v1,laguna_v1"]}),
        encoding="utf-8",
    )
    text = weekly_summary_markdown(tmp_path)
    assert "Artifact JSON files: **2**" in text
    assert "success=1.0" in text
    assert "quality=0.5" in text
    assert "winner=`hermes_v1,laguna_v1`" in text


def test_missing_secret_skips_without_posting(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "evals.summary_webhook.post_json_webhook",
        lambda *args, **kwargs: calls.append(args) or True,
    )
    result = notify_weekly_summary(
        "## Weekly benchmark summary",
        environ={"SLACK_WEBHOOK_URL": "  ", "DISCORD_WEBHOOK_URL": ""},
    )
    assert result == {"skipped": True, "sent": [], "failed": []}
    assert calls == []


def test_slack_post_uses_the_summary_text(monkeypatch):
    seen = {}

    def fake_post(url, payload, timeout=5.0):
        seen["url"] = url
        seen["payload"] = payload
        seen["timeout"] = timeout
        return True

    monkeypatch.setattr("evals.summary_webhook.post_json_webhook", fake_post)
    text = "## Weekly benchmark summary\n\nArtifact JSON files: **0**\n"
    result = notify_weekly_summary(
        text,
        environ={"SLACK_WEBHOOK_URL": "https://hooks.example/slack"},
    )
    assert result == {"skipped": False, "sent": ["slack"], "failed": []}
    assert seen["payload"] == {"text": text}


def test_discord_payload_is_truncated(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        "evals.summary_webhook.post_json_webhook",
        lambda url, payload, timeout=5.0: seen.update(payload) or True,
    )
    text = "x" * 3000
    result = notify_weekly_summary(
        text,
        environ={"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/1/token"},
    )
    assert result["sent"] == ["discord"]
    assert seen == message_payload("discord", text)
    assert seen["content"].endswith("\n…")
    assert len(seen["content"]) < 2000


def test_failed_post_is_reported(monkeypatch):
    monkeypatch.setattr("evals.summary_webhook.post_json_webhook", lambda *a, **k: False)
    result = notify_weekly_summary(
        "summary",
        environ={"SLACK_WEBHOOK_URL": "https://hooks.example/slack"},
    )
    assert result == {"skipped": False, "sent": [], "failed": ["slack"]}


def test_partial_delivery_names_the_failure(monkeypatch):
    def fake_post(url, payload, timeout=5.0):
        return "slack" in url

    monkeypatch.setattr("evals.summary_webhook.post_json_webhook", fake_post)
    result = notify_weekly_summary(
        "summary",
        environ={
            "SLACK_WEBHOOK_URL": "https://hooks.example/slack",
            "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/1/token",
        },
    )
    assert result["sent"] == ["slack"]
    assert result["failed"] == ["discord"]


def test_cli_fails_when_configured_post_fails(tmp_path, monkeypatch, capsys):
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example/slack")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("BENCHMARK_SUMMARY_WEBHOOK", raising=False)
    monkeypatch.setattr("evals.summary_webhook.post_json_webhook", lambda *a, **k: False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["weekly_summary.py", "--reports", str(reports), "--output", str(reports / "summary.md")],
    )
    assert main() == 1
    assert "failed for slack" in capsys.readouterr().out


def test_list_json_does_not_abort_summary(tmp_path):
    (tmp_path / "results.json").write_text(json.dumps([{"status": "success"}]), encoding="utf-8")
    text = weekly_summary_markdown(tmp_path)
    assert "results.json" in text
    assert "keys=[]" in text


def test_summary_notes_files_past_the_first_forty(tmp_path):
    for index in range(41):
        (tmp_path / f"r{index:02d}.json").write_text("{}", encoding="utf-8")
    text = weekly_summary_markdown(tmp_path)
    assert "Artifact JSON files: **41**" in text
    assert "1 more JSON files omitted" in text


def test_transport_error_returns_false_without_logging_the_url(caplog):
    secret = "https://hooks.slack.com/services/T/B/secret-token"

    def boom(*args, **kwargs):
        raise http.client.RemoteDisconnected(secret)

    with caplog.at_level(logging.WARNING):
        with patch("evals.alerts.urllib.request.urlopen", boom):
            assert post_json_webhook(secret, {"text": "hi"}) is False
    assert "secret-token" not in caplog.text


def test_cli_writes_summary_and_exits_when_unset(tmp_path, monkeypatch, capsys):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "full_easy.json").write_text(
        json.dumps({"overall": {"success_rate": 0.5, "avg_quality": 0.2}}),
        encoding="utf-8",
    )
    output = reports / "summary.md"
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("BENCHMARK_SUMMARY_WEBHOOK", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "weekly_summary.py",
            "--reports",
            str(reports),
            "--output",
            str(output),
        ],
    )
    assert main() == 0
    body = output.read_text(encoding="utf-8")
    assert "success=0.5" in body
    assert "Weekly summary webhook skipped" in capsys.readouterr().out


def test_evolution_doc_lists_every_workflow_cron():
    doc = (ROOT / "docs" / "Evolution.md").read_text(encoding="utf-8")
    for name in ("benchmark.yml", "ci-benchmark.yml", "nightly-evolution.yml"):
        workflow = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert name in doc
        for cron in re.findall(r'cron:\s*"([^"]+)"', workflow):
            assert cron in doc
    assert "OPENROUTER_API_KEY" in doc
    assert "--simulate" in doc
    assert "SLACK_WEBHOOK_URL" in doc
