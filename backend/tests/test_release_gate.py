from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import prepare_release


def test_production_release_migrates_and_checks_all_dependencies(monkeypatch):
    monkeypatch.setattr(prepare_release, "get_settings", lambda: SimpleNamespace(is_production=True))
    run = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(prepare_release.subprocess, "run", run)
    assert prepare_release.main() == 0
    commands = [call.args[0] for call in run.call_args_list]
    assert commands[0] == ["alembic", "upgrade", "head"]
    assert [command[1] for command in commands[1:]] == [
        "scripts/verify_production_postgres.py", "scripts/rotate_data_keys.py",
        "scripts/verify_production_redis.py", "scripts/verify_production_object_storage.py",
    ]
    assert "--redis-only" in commands[3]
    assert all(call.kwargs["capture_output"] is True for call in run.call_args_list)


@pytest.mark.parametrize("failed_stage", range(5))
def test_failed_prerequisite_stops_release_without_leaking_provider_output(monkeypatch, capsys, failed_stage):
    monkeypatch.setattr(prepare_release, "get_settings", lambda: SimpleNamespace(is_production=True))
    outcomes = [SimpleNamespace(returncode=0)] * failed_stage + [
        SimpleNamespace(returncode=1, stderr="private-provider-secret", stdout="private-url")]
    run = Mock(side_effect=outcomes)
    monkeypatch.setattr(prepare_release.subprocess, "run", run)
    assert prepare_release.main() == 1
    assert run.call_count == failed_stage + 1
    captured = capsys.readouterr()
    assert "private-provider-secret" not in captured.err
    assert "private-url" not in captured.err


def test_development_release_does_not_probe_production_providers(monkeypatch):
    monkeypatch.setattr(prepare_release, "get_settings", lambda: SimpleNamespace(is_production=False))
    run = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(prepare_release.subprocess, "run", run)
    assert prepare_release.main() == 0
    run.assert_called_once()
