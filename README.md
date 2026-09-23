# CRDT Set

A small Flask service demonstrating a Grow-only Set (G-Set) CRDT.

## Features
- Independent writes on replicas
- Conflict-free union merge
- Idempotent synchronization
- Replica comparison
- Thread-safe in-memory implementation
- Health and statistics endpoints
- Pytest test suite

## Run
```bash
pip install -r requirements.txt
python app.py
```

## API
- `POST /api/nodes`
- `GET /api/nodes`
- `DELETE /api/nodes/<node_id>`
- `POST /api/items`
- `GET /api/items/<node_id>`
- `GET /api/compare/<node_a>/<node_b>`
- `POST /api/merge/<node_a>/<node_b>`
- `GET /api/stats`
- `GET /health`

## CRDT Rule
The merge operation is set union:

`A ∪ B`

Union is associative, commutative, and idempotent, allowing replicas to converge after repeated or out-of-order synchronization.
