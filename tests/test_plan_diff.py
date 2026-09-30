"""Tests for plan diff."""

from backend.models import Assignment, Plan
from backend.state import CrisisState
from backend.diff import compute_plan_diff


def test_diff_detects_removed():
    before = Plan(id="P1", strategy_name="A", assignments=[
        Assignment(incident_id="I1", unit_id="U1", eta_minutes=5.0),
        Assignment(incident_id="I2", unit_id="U2", eta_minutes=3.0),
    ])
    after = Plan(id="P2", strategy_name="B", assignments=[
        Assignment(incident_id="I1", unit_id="U1", eta_minutes=5.0),
    ])
    state = CrisisState()
    diff = compute_plan_diff(before, after, state, "test")
    assert "I2" in diff.newly_uncovered


def test_diff_detects_added():
    before = Plan(id="P1", strategy_name="A", assignments=[
        Assignment(incident_id="I1", unit_id="U1"),
    ])
    after = Plan(id="P2", strategy_name="B", assignments=[
        Assignment(incident_id="I1", unit_id="U1"),
        Assignment(incident_id="I2", unit_id="U2"),
    ])
    state = CrisisState()
    diff = compute_plan_diff(before, after, state, "test")
    assert "I2" in diff.newly_covered


def test_diff_detects_unit_change():
    before = Plan(id="P1", strategy_name="A", assignments=[
        Assignment(incident_id="I1", unit_id="U1", eta_minutes=5.0),
    ])
    after = Plan(id="P2", strategy_name="B", assignments=[
        Assignment(incident_id="I1", unit_id="U3", eta_minutes=8.0),
    ])
    state = CrisisState()
    diff = compute_plan_diff(before, after, state, "breakdown")
    assert len(diff.changed_units) == 1
    assert diff.changed_units[0]["before_unit"] == "U1"
    assert diff.changed_units[0]["after_unit"] == "U3"


def test_diff_eta_changes():
    before = Plan(id="P1", strategy_name="A", assignments=[
        Assignment(incident_id="I1", unit_id="U1", eta_minutes=5.0),
    ])
    after = Plan(id="P2", strategy_name="B", assignments=[
        Assignment(incident_id="I1", unit_id="U1", eta_minutes=9.0),
    ])
    state = CrisisState()
    diff = compute_plan_diff(before, after, state, "road_block")
    assert "I1" in diff.eta_changes
    assert diff.eta_changes["I1"] == 4.0


def test_diff_explanation_has_trigger():
    before = Plan(id="P1", strategy_name="A", assignments=[])
    after = Plan(id="P2", strategy_name="B", assignments=[])
    state = CrisisState()
    diff = compute_plan_diff(before, after, state, "AMB-01 breakdown")
    assert "AMB-01 breakdown" in diff.explanation
