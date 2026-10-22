"""Managed UTF-8 YAML uses the strict JSON subset; Markdown is stored verbatim.

No general YAML authoring importer is provided by M1. Consequently YAML tags,
aliases, implicit scalars and duplicate keys cannot enter accepted metadata.
"""

import json

from second_brain_contracts.validation import _finite_float, _nonfinite, _unique


def encode(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def decode(raw):
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique,
        parse_constant=_nonfinite,
        parse_float=_finite_float,
    )
