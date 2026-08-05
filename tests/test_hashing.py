from tunegraph.services.hashing import canonical_json_bytes, sha256_json


def test_canonical_json_is_order_independent() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert sha256_json(left) == sha256_json(right)
