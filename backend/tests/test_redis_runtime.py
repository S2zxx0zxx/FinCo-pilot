import pytest

from app.core.redis_runtime import parse_redis_target, validate_redis_target


def test_parse_redis_target_hides_credentials_and_extracts_transport():
    target = parse_redis_target("rediss://default:secret@example.redis.test:6380/0")
    assert target.scheme == "rediss"
    assert target.hostname == "example.redis.test"
    assert target.port == 6380
    assert target.database == 0
    assert target.authenticated is True
    assert target.tls is True


@pytest.mark.parametrize(
    "url",
    [
        "http://redis.example/0",
        "redis:///0",
        "redis://redis.example/not-a-db",
    ],
)
def test_parse_redis_target_rejects_invalid_targets(url):
    with pytest.raises(ValueError):
        parse_redis_target(url)


def test_external_redis_rejects_bundled_hosts():
    with pytest.raises(ValueError, match="external Redis"):
        validate_redis_target(
            "redis://redis:6379/0",
            external_required=True,
            tls_required=False,
            auth_required=False,
        )


def test_tls_and_auth_can_be_required_independently():
    with pytest.raises(ValueError, match="rediss"):
        validate_redis_target(
            "redis://:secret@redis.example.test:6379/0",
            external_required=True,
            tls_required=True,
            auth_required=True,
        )
    with pytest.raises(ValueError, match="authenticated"):
        validate_redis_target(
            "rediss://redis.example.test:6380/0",
            external_required=True,
            tls_required=True,
            auth_required=True,
        )


def test_external_tls_authenticated_target_passes():
    target = validate_redis_target(
        "rediss://default:secret@redis.example.test:6380/0",
        external_required=True,
        tls_required=True,
        auth_required=True,
    )
    assert target.hostname == "redis.example.test"
