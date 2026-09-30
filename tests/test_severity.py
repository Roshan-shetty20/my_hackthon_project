"""Tests for severity scoring engine."""

from backend.models import Incident, UnitType, UrgencyLevel
from backend.severity import calculate_severity, get_urgency, assess_incident


def _make_incident(**kwargs):
    defaults = dict(
        id="T", type="Test", location="A", latitude=0, longitude=0,
        people_affected=0, people_trapped=0, vulnerable_people=0,
        life_threat=False, time_critical=False, spreading_hazard=False,
        required_units={UnitType.AMBULANCE: 1},
    )
    defaults.update(kwargs)
    return Incident(**defaults)


def test_low_incident():
    inc = _make_incident(people_affected=2, time_critical=False)
    score = calculate_severity(inc)
    assert 1 <= score <= 3, f"Expected LOW range, got {score}"


def test_medium_incident():
    inc = _make_incident(people_affected=10, time_critical=True)
    score = calculate_severity(inc)
    assert 4 <= score <= 6, f"Expected MEDIUM range, got {score}"


def test_high_incident():
    inc = _make_incident(people_affected=10, people_trapped=2, life_threat=True)
    score = calculate_severity(inc)
    assert 7 <= score <= 8, f"Expected HIGH range, got {score}"


def test_critical_incident():
    inc = _make_incident(
        people_affected=25, people_trapped=8, vulnerable_people=3,
        life_threat=True, time_critical=True, spreading_hazard=True,
    )
    score = calculate_severity(inc)
    assert score >= 9, f"Expected CRITICAL (>=9), got {score}"


def test_missing_data_penalty():
    """All numeric fields zero → uncertainty penalty applied."""
    inc = _make_incident()
    score = calculate_severity(inc)
    assert score >= 2, "Expected uncertainty penalty to raise score above 1"


def test_severity_clamped():
    inc = _make_incident(
        people_affected=100, people_trapped=100, vulnerable_people=100,
        life_threat=True, time_critical=True, spreading_hazard=True,
    )
    score = calculate_severity(inc)
    assert score == 10, "Score must be clamped to 10"


def test_urgency_bands():
    assert get_urgency(1) == UrgencyLevel.LOW
    assert get_urgency(3) == UrgencyLevel.LOW
    assert get_urgency(4) == UrgencyLevel.MEDIUM
    assert get_urgency(6) == UrgencyLevel.MEDIUM
    assert get_urgency(7) == UrgencyLevel.HIGH
    assert get_urgency(8) == UrgencyLevel.HIGH
    assert get_urgency(9) == UrgencyLevel.CRITICAL
    assert get_urgency(10) == UrgencyLevel.CRITICAL


def test_assess_incident_sets_fields():
    inc = _make_incident(people_affected=25, life_threat=True, time_critical=True)
    assess_incident(inc)
    assert inc.severity is not None
    assert inc.urgency is not None
