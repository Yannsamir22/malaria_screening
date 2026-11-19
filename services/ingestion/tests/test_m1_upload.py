def test_health_is_public(client):
      resp = client.get("/api/v1/health")
      assert resp.status_code == 200
      assert resp.json() == {"status": "ok", "service": "ingestion-service"}