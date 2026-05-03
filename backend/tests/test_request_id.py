from uuid import UUID


def test_response_includes_generated_request_id(client):
    response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("x-request-id")
    assert request_id
    UUID(request_id)


def test_response_reuses_incoming_request_id(client):
    response = client.get("/health", headers={"X-Request-ID": "client-request-123"})

    assert response.status_code == 200
    assert response.headers.get("x-request-id") == "client-request-123"


def test_auth_failure_response_includes_request_id(client):
    response = client.get(
        "/me",
        headers={
            "Authorization": "Bearer invalid-token",
            "X-Request-ID": "auth-failure-request",
        },
    )

    assert response.status_code == 401
    assert response.headers.get("x-request-id") == "auth-failure-request"
