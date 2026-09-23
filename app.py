from threading import RLock
from flask import Flask, jsonify, request

app = Flask(__name__)
LOCK = RLock()
DEFAULT_NODES = ("node-1", "node-2", "node-3")


class GSetCluster:
    def __init__(self):
        self.nodes = {}
        self.merge_rounds = 0
        self.merge_counts = {}
        for node in DEFAULT_NODES:
            self.add_node(node)

    def add_node(self, node_id):
        if not node_id or len(node_id) > 64:
            raise ValueError("node_id must contain 1-64 characters")
        if node_id not in self.nodes:
            self.nodes[node_id] = set()
            self.merge_counts[node_id] = 0

    def remove_node(self, node_id):
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.merge_counts.pop(node_id, None)
            return True
        return False

    def add_item(self, node_id, item):
        if node_id not in self.nodes:
            raise KeyError("node not found")
        if not isinstance(item, str) or not item.strip():
            raise ValueError("item must be a non-empty string")
        item = item.strip()
        before = len(self.nodes[node_id])
        self.nodes[node_id].add(item)
        return {"item": item, "added": len(self.nodes[node_id]) > before,
                "size": len(self.nodes[node_id])}

    def compare(self, node_a, node_b):
        if node_a not in self.nodes or node_b not in self.nodes:
            raise KeyError("node not found")
        a, b = self.nodes[node_a], self.nodes[node_b]
        return {
            "node_a": node_a, "node_b": node_b,
            "only_in_a": sorted(a - b),
            "only_in_b": sorted(b - a),
            "common": sorted(a & b),
            "equal": a == b,
        }

    def merge(self, node_a, node_b):
        if node_a not in self.nodes or node_b not in self.nodes:
            raise KeyError("node not found")
        if node_a == node_b:
            raise ValueError("nodes must be different")

        before_a = len(self.nodes[node_a])
        before_b = len(self.nodes[node_b])
        combined = self.nodes[node_a] | self.nodes[node_b]
        self.nodes[node_a] = set(combined)
        self.nodes[node_b] = set(combined)

        added_a = len(combined) - before_a
        added_b = len(combined) - before_b
        self.merge_rounds += 1
        self.merge_counts[node_a] += 1
        self.merge_counts[node_b] += 1

        return {
            "round": self.merge_rounds,
            "node_a": node_a, "node_b": node_b,
            "added_to_a": added_a, "added_to_b": added_b,
            "size": len(combined), "converged": True,
        }

    def stats(self):
        return {
            "nodes": len(self.nodes),
            "merge_rounds": self.merge_rounds,
            "merge_counts": dict(self.merge_counts),
            "total_unique_items": sum(len(x) for x in self.nodes.values()),
        }


cluster = GSetCluster()

@app.get("/health")
def health():
    return jsonify({"status": "ok", "nodes": len(cluster.nodes)})

@app.get("/api/nodes")
def list_nodes():
    with LOCK:
        return jsonify({"nodes": sorted(cluster.nodes)})

@app.post("/api/nodes")
def add_node():
    body = request.get_json(silent=True) or {}
    node_id = str(body.get("node_id", "")).strip()
    try:
        with LOCK:
            if node_id in cluster.nodes:
                return jsonify({"error": "node already exists"}), 409
            cluster.add_node(node_id)
        return jsonify({"node_id": node_id, "created": True}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

@app.delete("/api/nodes/<node_id>")
def remove_node(node_id):
    with LOCK:
        if not cluster.remove_node(node_id):
            return jsonify({"error": "node not found"}), 404
    return jsonify({"node_id": node_id, "removed": True})

@app.post("/api/items")
def add_item():
    body = request.get_json(silent=True) or {}
    node_id = str(body.get("node_id", "")).strip()
    try:
        with LOCK:
            result = cluster.add_item(node_id, body.get("item"))
        return jsonify({"node_id": node_id, **result}), 201
    except KeyError:
        return jsonify({"error": "node not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

@app.get("/api/items/<node_id>")
def get_items(node_id):
    with LOCK:
        if node_id not in cluster.nodes:
            return jsonify({"error": "node not found"}), 404
        items = sorted(cluster.nodes[node_id])
        return jsonify({"node_id": node_id, "items": items, "count": len(items)})

@app.get("/api/compare/<node_a>/<node_b>")
def compare(node_a, node_b):
    try:
        with LOCK:
            return jsonify(cluster.compare(node_a, node_b))
    except KeyError:
        return jsonify({"error": "node not found"}), 404

@app.post("/api/merge/<node_a>/<node_b>")
def merge(node_a, node_b):
    try:
        with LOCK:
            return jsonify(cluster.merge(node_a, node_b))
    except KeyError:
        return jsonify({"error": "node not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

@app.get("/api/stats")
def stats():
    with LOCK:
        return jsonify(cluster.stats())

if __name__ == "__main__":
    app.run(debug=True)
