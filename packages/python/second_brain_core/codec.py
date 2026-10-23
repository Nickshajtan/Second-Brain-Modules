"""Managed UTF-8 YAML uses the strict JSON subset; Markdown is stored verbatim.

No general YAML authoring importer is provided by M1. Consequently YAML tags,
aliases, implicit scalars and duplicate keys cannot enter accepted metadata.
"""

from second_brain_contracts import decode_json, encode_json


def encode(value: object) -> bytes:
    return encode_json(value)


def decode(raw: bytes) -> dict:
    """Managed records are objects; arbitrary JSON uses contracts.decode_json."""
    value = decode_json(raw)
    if not isinstance(value, dict):
        raise ValueError("Managed record must be a JSON object")
    return value
