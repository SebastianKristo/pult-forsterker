"""docs/api/openapi.yaml skal være gyldig OpenAPI 3.1 (regenereres med python3 docs/api/gen_openapi.py)."""
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_openapi_gyldig():
    yaml = pytest.importorskip("yaml")
    osv = pytest.importorskip("openapi_spec_validator")
    spec = yaml.safe_load(open(os.path.join(ROOT, "docs/api/openapi.yaml"), encoding="utf-8"))
    osv.validate(spec)
    for p in ("/api/status", "/api/events", "/api/volume", "/api/cloud", "/api/matter"):
        assert p in spec["paths"]
