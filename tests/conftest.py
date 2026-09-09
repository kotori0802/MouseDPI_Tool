from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "golden"
POLICY = json.loads((FIXTURES / "00_fixture_policy.json").read_text(encoding="utf-8"))


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def project(row: dict, fields: list[str]) -> dict:
    return {k: row.get(k) for k in fields}


@pytest.fixture(scope="module")
def trial_fields():
    return POLICY["compare_trial_fields"]


@pytest.fixture(scope="module")
def group_fields():
    return POLICY["compare_group_fields"]


@pytest.fixture(scope="module")
def ratio_fields():
    return POLICY["compare_ratio_fields"]
