import pytest

from scripts.native_test_database import validate_native_test_target


TARGET = "postgresql+asyncpg://finco_ci:synthetic-test-password@localhost:5432/finco_ci"


def environment(target=TARGET):
    return {
        "DATABASE_URL": target,
        "DEPLOYMENT_ENVIRONMENT": "development",
        "FINCO_DISPOSABLE_DB_TEST": "yes",
    }


def test_disposable_local_target_is_accepted():
    validate_native_test_target(TARGET, environment())


@pytest.mark.parametrize("target", [
    "not-a-database-url",
    TARGET.replace("localhost", "production.neon.tech"),
    TARGET.replace("localhost", "localhost.example.com"),
    TARGET.replace("/finco_ci", "/production"),
    TARGET.replace("//finco_ci:", "//production:"),
    TARGET.replace("postgresql+asyncpg", "sqlite+aiosqlite"),
    TARGET + "?host=production.neon.tech",
])
def test_other_database_targets_are_rejected(target):
    with pytest.raises(RuntimeError):
        validate_native_test_target(target, environment(target))


@pytest.mark.parametrize("key,value", [
    ("DATABASE_URL", TARGET.replace("/finco_ci", "/different")),
    ("DEPLOYMENT_ENVIRONMENT", "production"),
    ("DEPLOYMENT_ENVIRONMENT", "staging"),
    ("FINCO_DISPOSABLE_DB_TEST", ""),
])
def test_explicit_isolation_guards_are_required(key, value):
    env = environment()
    env[key] = value
    with pytest.raises(RuntimeError):
        validate_native_test_target(TARGET, env)
