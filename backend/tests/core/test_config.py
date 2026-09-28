from app.core.config import Settings


def test_settings_accept_legacy_phase_zero_environment_names() -> None:
    """確認現有 .env 的舊名稱在 migration 期間仍可正確載入。"""

    settings = Settings(
        _env_file=None,
        FRONTEND_ORIGIN="https://fish-sniper.example",
        JWT_SECRET="legacy-jwt-secret",
        SUPABASE_SERVICE_ROLE_KEY="legacy-service-role-key",
        GOOGLE_OAUTH_ALLOWED_REDIRECT_URIS=(
            "http://localhost:5173/auth/google/callback,"
            "https://fish-sniper.example/auth/google/callback"
        ),
    )

    assert settings.cors_origin_list == ["https://fish-sniper.example"]
    assert settings.jwt_secret_key == "legacy-jwt-secret"
    assert settings.supabase_secret_key == "legacy-service-role-key"
    assert settings.google_oauth_allowed_redirect_uri_list == [
        "http://localhost:5173/auth/google/callback",
        "https://fish-sniper.example/auth/google/callback",
    ]
