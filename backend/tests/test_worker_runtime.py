from app.worker import celery_app, health_probe


def test_worker_transport_is_bounded_and_retry_safe():
    assert celery_app.conf.broker_connection_retry_on_startup is True
    assert celery_app.conf.worker_prefetch_multiplier >= 1
    assert 60 <= celery_app.conf.result_expires <= 604800
    assert celery_app.conf.broker_transport_options["visibility_timeout"] >= 60


def test_health_probe_is_side_effect_free():
    assert health_probe.run("nonce-123") == {"ok": True, "nonce": "nonce-123"}


def test_beat_schedule_has_unique_static_entries():
    schedule = celery_app.conf.beat_schedule
    assert schedule
    assert len(schedule) == len(set(schedule))
    assert all(entry.get("task") for entry in schedule.values())
