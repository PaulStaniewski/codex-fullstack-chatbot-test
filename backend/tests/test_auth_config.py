import pytest

from app.auth import _resolve_auth_settings


def test_missing_secret_in_production_fails():
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be set"):
        _resolve_auth_settings(
            {
                "APP_ENV": "production",
                "JWT_ALGORITHM": "HS256",
                "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
            }
        )


def test_default_or_dev_secret_in_production_fails():
    with pytest.raises(RuntimeError, match="unsafe for production"):
        _resolve_auth_settings(
            {
                "APP_ENV": "production",
                "JWT_SECRET_KEY": "change-me-in-production",
                "JWT_ALGORITHM": "HS256",
                "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
            }
        )

    with pytest.raises(RuntimeError, match="unsafe for production"):
        _resolve_auth_settings(
            {
                "APP_ENV": "prod",
                "JWT_SECRET_KEY": "dev-only-jwt-secret-change-this",
            }
        )


def test_valid_secret_works_in_production():
    secret, algorithm, expire_minutes = _resolve_auth_settings(
        {
            "APP_ENV": "production",
            "JWT_SECRET_KEY": "prod-secret-2026-very-long-and-unique",
            "JWT_ALGORITHM": "HS256",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "45",
        }
    )

    assert secret == "prod-secret-2026-very-long-and-unique"
    assert algorithm == "HS256"
    assert expire_minutes == 45


def test_test_and_dev_configs_remain_usable():
    dev_secret, _, _ = _resolve_auth_settings(
        {
            "APP_ENV": "development",
            "JWT_SECRET_KEY": "dev-only-jwt-secret-change-this",
        }
    )
    test_secret, _, _ = _resolve_auth_settings(
        {
            "APP_ENV": "test",
            "JWT_SECRET_KEY": "test-secret-key",
        }
    )

    assert dev_secret == "dev-only-jwt-secret-change-this"
    assert test_secret == "test-secret-key"
