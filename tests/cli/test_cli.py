from __future__ import annotations

import pytest

from zotomatic import cli
from zotomatic.errors import ZotomaticError


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    cli.main([])
    captured = capsys.readouterr()
    assert "Zotomatic command-line interface" in captured.out


def test_cli_version(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "__version__", "0.2.0")
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "0.2.0"


def test_cli_dispatch_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_run_scan(options):
        called["options"] = options

    monkeypatch.setattr(cli.pipelines, "run_scan", fake_run_scan)
    cli.main(["scan", "--once"])
    assert called["options"]["once"] is True


def test_cli_dispatch_template_create(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_template_create(options):
        called["options"] = options

    monkeypatch.setattr(cli.pipelines, "run_template_create", fake_template_create)
    cli.main(["template", "create", "--path", "/tmp/tpl.md"])
    assert called["options"]["template_path"] == "/tmp/tpl.md"


def test_cli_dispatch_config_show(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_run_config_show(options):
        called["options"] = options

    monkeypatch.setattr(cli.pipelines, "run_config_show", fake_run_config_show)
    cli.main(["config", "show"])
    assert called["options"] == {}


def test_cli_dispatch_config_default_show(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_run_config_show(options):
        called["options"] = options

    monkeypatch.setattr(cli.pipelines, "run_config_show", fake_run_config_show)
    cli.main(["config"])
    assert called["options"] == {}


def test_cli_dispatch_config_default(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_run_config_default(options):
        called["options"] = options

    monkeypatch.setattr(cli.pipelines, "run_config_default", fake_run_config_default)
    cli.main(["config", "default"])
    assert called["options"] == {}


def test_cli_error_handling(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run_scan(_options):
        raise ZotomaticError("boom", hint="fix")

    monkeypatch.setattr(cli.pipelines, "run_scan", fake_run_scan)
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["scan", "--once"])
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "zotomatic: error: boom" in captured.err
    assert "zotomatic: hint: fix" in captured.err
