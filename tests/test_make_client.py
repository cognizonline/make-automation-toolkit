#!/usr/bin/env python3
"""
Unit tests for MakeClient.

Uses the `responses` library to mock HTTP so no real network calls are made.
Run with: pytest tests/ -v --cov=src
"""
import json
import sys
import time
from pathlib import Path

import responses as resp_lib
import pytest

# Allow importing src/ without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from make_client import MakeClient, MakeDeployer  # noqa: E402


BASE_URL = "https://eu1.make.com/api/v2"


def make_client() -> MakeClient:
    return MakeClient(
        api_token="test-token",
        zone="eu1.make.com",
        team_id=42,
    )


# ---------------------------------------------------------------------------
# list_scenarios
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_list_scenarios_happy_path():
    resp_lib.add(
        resp_lib.GET,
        f"{BASE_URL}/scenarios",
        json={"scenarios": [{"id": 1, "name": "My Scenario"}]},
        status=200,
    )
    client = make_client()
    result = client.list_scenarios()
    assert result == [{"id": 1, "name": "My Scenario"}]
    assert resp_lib.calls[0].request.params["teamId"] == "42"


@resp_lib.activate
def test_list_scenarios_with_folder():
    resp_lib.add(
        resp_lib.GET,
        f"{BASE_URL}/scenarios",
        json={"scenarios": []},
        status=200,
    )
    client = make_client()
    client.list_scenarios(folder_id=99)
    params = resp_lib.calls[0].request.params
    assert params["folderId"] == "99"


# ---------------------------------------------------------------------------
# create_scenario
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_create_scenario_happy_path():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/scenarios",
        json={"scenario": {"id": 7}},
        status=200,
    )
    client = make_client()
    blueprint = {"name": "Test", "flow": [{"id": 1, "module": "util:SetVariable2"}], "metadata": {"version": 1}}
    scenario_id = client.create_scenario(blueprint)
    assert scenario_id == 7


@resp_lib.activate
def test_create_scenario_blueprint_is_json_stringified():
    """The API expects blueprint as a JSON string, not a nested object."""
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/scenarios",
        json={"scenario": {"id": 8}},
        status=200,
    )
    client = make_client()
    blueprint = {"name": "Test", "flow": [{"id": 1, "module": "util:SetVariable2"}], "metadata": {"version": 1}}
    client.create_scenario(blueprint)

    sent_body = json.loads(resp_lib.calls[0].request.body)
    # blueprint must be a string (JSON-encoded), not a dict
    assert isinstance(sent_body["blueprint"], str)
    decoded = json.loads(sent_body["blueprint"])
    assert decoded["name"] == "Test"


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_run_scenario_without_data():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/scenarios/10/run",
        json={"executionId": "exec-abc", "status": "success"},
        status=200,
    )
    client = make_client()
    result = client.run_scenario(10)
    assert result["executionId"] == "exec-abc"
    sent_body = json.loads(resp_lib.calls[0].request.body)
    assert "data" not in sent_body


@resp_lib.activate
def test_run_scenario_with_data():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/scenarios/10/run",
        json={"executionId": "exec-xyz", "status": "success"},
        status=200,
    )
    client = make_client()
    result = client.run_scenario(10, data={"order_id": "ORD-123"})
    assert result["status"] == "success"
    sent_body = json.loads(resp_lib.calls[0].request.body)
    assert sent_body["data"] == {"order_id": "ORD-123"}


# ---------------------------------------------------------------------------
# _request retry on 429 with exponential backoff
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_request_retries_on_429_then_succeeds(monkeypatch):
    """First call returns 429; second returns 200."""
    call_count = {"n": 0}
    sleeps = []

    def fake_sleep(secs):
        sleeps.append(secs)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    resp_lib.add(resp_lib.GET, f"{BASE_URL}/scenarios", json={}, status=429)
    resp_lib.add(
        resp_lib.GET,
        f"{BASE_URL}/scenarios",
        json={"scenarios": [{"id": 99}]},
        status=200,
    )

    client = make_client()
    result = client.list_scenarios()
    assert result == [{"id": 99}]
    # Should have slept once (exponential backoff for attempt 0 = 2^0 = 1)
    assert len(sleeps) == 1
    assert sleeps[0] == 1  # 2^0 = 1, no Retry-After header


# ---------------------------------------------------------------------------
# _request respects Retry-After header on 429
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_request_uses_retry_after_header(monkeypatch):
    """When server sends Retry-After: 30, we sleep 30s, not 2^attempt."""
    sleeps = []

    def fake_sleep(secs):
        sleeps.append(secs)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    resp_lib.add(
        resp_lib.GET,
        f"{BASE_URL}/scenarios",
        json={},
        status=429,
        headers={"Retry-After": "30"},
    )
    resp_lib.add(
        resp_lib.GET,
        f"{BASE_URL}/scenarios",
        json={"scenarios": []},
        status=200,
    )

    client = make_client()
    client.list_scenarios()
    assert sleeps[0] == 30


# ---------------------------------------------------------------------------
# create_data_structure
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_create_data_structure_returns_id():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/data-structures",
        json={"dataStructure": {"id": 55, "name": "Orders"}},
        status=200,
    )
    client = make_client()
    spec = [{"name": "order_id", "type": "text"}]
    ds_id = client.create_data_structure("Orders", spec)
    assert ds_id == 55


# ---------------------------------------------------------------------------
# add_record
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_add_record_without_key():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/data-stores/5/data",
        json={"record": {"key": "auto-key", "data": {"x": 1}}},
        status=200,
    )
    client = make_client()
    result = client.add_record(5, {"x": 1})
    sent_body = json.loads(resp_lib.calls[0].request.body)
    assert "key" not in sent_body
    assert sent_body["data"] == {"x": 1}


@resp_lib.activate
def test_add_record_with_key():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/data-stores/5/data",
        json={"record": {"key": "my-key", "data": {"x": 2}}},
        status=200,
    )
    client = make_client()
    client.add_record(5, {"x": 2}, key="my-key")
    sent_body = json.loads(resp_lib.calls[0].request.body)
    assert sent_body["key"] == "my-key"


# ---------------------------------------------------------------------------
# verify_connection
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_verify_connection_returns_true():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/connections/77/verify",
        json={"verified": True},
        status=200,
    )
    client = make_client()
    assert client.verify_connection(77) is True


@resp_lib.activate
def test_verify_connection_returns_false():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE_URL}/connections/77/verify",
        json={"verified": False},
        status=200,
    )
    client = make_client()
    assert client.verify_connection(77) is False


# ---------------------------------------------------------------------------
# paginate_scenarios (pagination generator)
# ---------------------------------------------------------------------------


@resp_lib.activate
def test_paginate_scenarios_single_page():
    """When first page has fewer items than page_size, generator stops after one call."""
    resp_lib.add(
        resp_lib.GET,
        f"{BASE_URL}/scenarios",
        json={"scenarios": [{"id": 1}, {"id": 2}]},
        status=200,
    )
    client = make_client()
    results = list(client.paginate_scenarios(page_size=100))
    assert results == [{"id": 1}, {"id": 2}]
    assert len(resp_lib.calls) == 1


@resp_lib.activate
def test_paginate_scenarios_multiple_pages():
    """Full page triggers a second request; partial second page stops iteration."""
    # Page 1: full (2 items, page_size=2)
    resp_lib.add(
        resp_lib.GET,
        f"{BASE_URL}/scenarios",
        json={"scenarios": [{"id": 1}, {"id": 2}]},
        status=200,
    )
    # Page 2: partial (1 item < page_size=2) — stops
    resp_lib.add(
        resp_lib.GET,
        f"{BASE_URL}/scenarios",
        json={"scenarios": [{"id": 3}]},
        status=200,
    )

    client = make_client()
    results = list(client.paginate_scenarios(page_size=2))
    assert [r["id"] for r in results] == [1, 2, 3]
    assert len(resp_lib.calls) == 2
    # Second call should have offset=2
    assert resp_lib.calls[1].request.params["pg[offset]"] == "2"
