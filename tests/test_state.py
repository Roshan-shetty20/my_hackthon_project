"""Tests for crisis state management."""

from backend.models import Incident, Unit, UnitStatus, UnitType
from backend.state import CrisisState, StateHistory


def test_version_increments():
    state = CrisisState()
    assert state.version == 1
    state.increment_version()
    assert state.version == 2


def test_snapshot_is_independent():
    state = CrisisState()
    state.units.append(
        Unit(id="U1", type=UnitType.AMBULANCE, status=UnitStatus.AVAILABLE)
    )
    snap = state.snapshot()
    state.units[0].status = UnitStatus.BROKEN_DOWN
    assert snap.units[0].status == UnitStatus.AVAILABLE


def test_history_saves_and_retrieves():
    history = StateHistory()
    state = CrisisState()
    state.log_action("Test", "action1")
    history.save(state)
    state.increment_version()
    state.log_action("Test", "action2")
    history.save(state)

    v1 = history.get_version(1)
    assert v1 is not None
    assert len(v1.action_log) == 1

    latest = history.latest()
    assert latest is not None
    assert latest.version == 2


def test_get_unit():
    state = CrisisState(units=[
        Unit(id="U1", type=UnitType.AMBULANCE),
        Unit(id="U2", type=UnitType.RESCUE_TEAM),
    ])
    assert state.get_unit("U1") is not None
    assert state.get_unit("U1").type == UnitType.AMBULANCE
    assert state.get_unit("NOPE") is None


def test_get_available_units():
    state = CrisisState(units=[
        Unit(id="U1", type=UnitType.AMBULANCE, status=UnitStatus.AVAILABLE),
        Unit(id="U2", type=UnitType.AMBULANCE, status=UnitStatus.BROKEN_DOWN),
    ])
    avail = state.get_available_units()
    assert len(avail) == 1
    assert avail[0].id == "U1"
