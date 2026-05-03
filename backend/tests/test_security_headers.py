from app.observability import build_content_security_policy


SECURITY_HEADER_EXPECTATIONS = {
    "content-security-policy": "default-src 'self'",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=()",
}


def _assert_security_headers(response):
    for header_name, expected_value in SECURITY_HEADER_EXPECTATIONS.items():
        assert header_name in response.headers
        assert expected_value in response.headers[header_name]


def test_security_headers_exist_on_normal_response(client):
    response = client.get("/health")

    assert response.status_code == 200
    _assert_security_headers(response)
    csp = response.headers["content-security-policy"]
    assert "script-src 'self'" in csp
    assert "connect-src" in csp
    assert "http://localhost:5173" in csp
    assert "'unsafe-inline'" not in csp


def test_security_headers_exist_on_error_response(client):
    response = client.get("/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
    _assert_security_headers(response)


def test_production_csp_is_stricter(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    csp = build_content_security_policy()

    assert "connect-src 'self'" in csp
    assert "localhost:5173" not in csp
    assert "upgrade-insecure-requests" in csp
