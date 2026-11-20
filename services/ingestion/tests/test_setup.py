import pytest

from app.config import Settings
from app.main import create_app
from conformance import app_operations, check_response, spec_operations
from tokens import SECRET

pytestmark = pytest.mark.m0


def test_health_is_public(client):
    r = client.get("/api/v1/health")
    check_response(r, "GET", "/api/v1/health")
    assert r.json() == {"status": "ok", "service": "ingestion-service"}


def test_the_app_serves_exactly_the_operations_of_the_yaml():
    app = create_app(Settings(jwt_secret=SECRET))
    assert app_operations(app) == spec_operations()


def test_a_short_secret_is_refused():
    with pytest.raises(RuntimeError):
        Settings(jwt_secret="short")
