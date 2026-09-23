import pytest
import app as module

@pytest.fixture(autouse=True)
def reset_cluster():
    module.cluster = module.GSetCluster()
    yield

@pytest.fixture
def client():
    module.app.config["TESTING"] = True
    return module.app.test_client()

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"

def test_add_item(client):
    r = client.post("/api/items", json={"node_id": "node-1", "item": "apple"})
    assert r.status_code == 201
    assert r.get_json()["added"] is True

def test_duplicate_is_idempotent(client):
    payload = {"node_id": "node-1", "item": "apple"}
    client.post("/api/items", json=payload)
    r = client.post("/api/items", json=payload)
    assert r.status_code == 201
    assert r.get_json()["added"] is False
    assert client.get("/api/items/node-1").get_json()["count"] == 1

def test_merge_converges(client):
    client.post("/api/items", json={"node_id": "node-1", "item": "apple"})
    client.post("/api/items", json={"node_id": "node-2", "item": "banana"})
    r = client.post("/api/merge/node-1/node-2")
    assert r.status_code == 200
    assert client.get("/api/items/node-1").get_json()["items"] == ["apple", "banana"]
    assert client.get("/api/items/node-2").get_json()["items"] == ["apple", "banana"]

def test_merge_is_idempotent(client):
    client.post("/api/items", json={"node_id": "node-1", "item": "apple"})
    client.post("/api/merge/node-1/node-2")
    r = client.post("/api/merge/node-1/node-2").get_json()
    assert r["added_to_a"] == 0
    assert r["added_to_b"] == 0

def test_compare_detects_difference(client):
    client.post("/api/items", json={"node_id": "node-1", "item": "apple"})
    client.post("/api/items", json={"node_id": "node-2", "item": "banana"})
    r = client.get("/api/compare/node-1/node-2").get_json()
    assert r["only_in_a"] == ["apple"]
    assert r["only_in_b"] == ["banana"]
    assert r["equal"] is False
