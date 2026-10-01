from app.core.retention import (
    BACKUP_MAX_RETENTION_DAYS,
    CERT_IN_ICT_LOG_REFERENCE_DAYS,
    DPDP_FUTURE_LOG_REFERENCE_DAYS,
    RETENTION_RULES,
    SECURITY_LOG_RETENTION_DAYS,
    DeletionMode,
    RetentionMode,
    get_retention_rule,
)


def test_retention_registry_is_self_keyed_and_complete():
    assert len(RETENTION_RULES) >= 15
    for key, rule in RETENTION_RULES.items():
        assert rule.key == key
        assert rule.notes.strip()


def test_security_log_window_covers_policy_reference_points():
    # Engineering policy is deliberately conservative. These reference values
    # are documented legal/future-law anchors, not proof of deployment.
    assert SECURITY_LOG_RETENTION_DAYS >= CERT_IN_ICT_LOG_REFERENCE_DAYS
    assert SECURITY_LOG_RETENTION_DAYS >= DPDP_FUTURE_LOG_REFERENCE_DAYS


def test_ephemeral_state_never_enters_backup_contract():
    rule = get_retention_rule("authentication_challenges_and_rate_limits")
    assert rule.mode is RetentionMode.EPHEMERAL_TTL
    assert rule.deletion is DeletionMode.EXPIRE_BY_TTL
    assert rule.backup_days is None


def test_generated_exports_are_not_server_persisted():
    rule = get_retention_rule("user_generated_exports")
    assert rule.mode is RetentionMode.NOT_SERVER_PERSISTED
    assert rule.deletion is DeletionMode.NOT_APPLICABLE
    assert rule.backup_days is None


def test_production_backup_window_is_bounded():
    rule = get_retention_rule("production_backups")
    assert rule.mode is RetentionMode.ROLLING_DAYS
    assert rule.days == BACKUP_MAX_RETENTION_DAYS == 30
    assert rule.backup_days is None


def test_all_configured_day_windows_are_positive_and_backup_copies_stay_bounded():
    # Do not impose a global 365-day ceiling: a later, documented legal or
    # provider requirement may legitimately need a longer record-specific
    # window. Normal backup copies remain independently capped by this policy.
    for rule in RETENTION_RULES.values():
        if rule.days is not None:
            assert rule.days > 0
        if rule.backup_days is not None:
            assert 0 < rule.backup_days <= BACKUP_MAX_RETENTION_DAYS


def test_unknown_category_fails_closed():
    try:
        get_retention_rule("new_unreviewed_store")
    except KeyError as exc:
        assert "Unknown retention category" in str(exc)
    else:
        raise AssertionError("Unknown categories must not silently inherit a default")
