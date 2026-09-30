"""
Crisis Command — Severity Scoring Engine

PROTOTYPE DECISION POLICY — NOT MEDICALLY VALIDATED.
This is the project's prototype severity formula for simulation purposes.

Deterministic scoring formula (all weights documented here):

  Base score: 1

  People affected:
    > 20  →  +3
    > 5   →  +2
    > 0   →  +1

  People trapped:
    > 5   →  +3
    > 0   →  +2

  Vulnerable people:
    > 2   →  +2
    > 0   →  +1

  Life threat:       +3
  Time-critical:     +2
  Spreading hazard:  +1

  Missing/zero data across all numeric fields:  +1 (uncertainty penalty)

  Final score clamped to [1, 10].

Urgency bands:
  1–3   LOW
  4–6   MEDIUM
  7–8   HIGH
  9–10  CRITICAL
"""

from backend.models import Incident, UrgencyLevel


# ---------------------------------------------------------------------------
# Severity weights — single source of truth
# ---------------------------------------------------------------------------

PEOPLE_AFFECTED_HIGH_THRESHOLD = 20
PEOPLE_AFFECTED_MED_THRESHOLD = 5

PEOPLE_TRAPPED_HIGH_THRESHOLD = 5

VULNERABLE_HIGH_THRESHOLD = 2

SCORE_PEOPLE_AFFECTED_HIGH = 3
SCORE_PEOPLE_AFFECTED_MED = 2
SCORE_PEOPLE_AFFECTED_LOW = 1

SCORE_PEOPLE_TRAPPED_HIGH = 3
SCORE_PEOPLE_TRAPPED_LOW = 2

SCORE_VULNERABLE_HIGH = 2
SCORE_VULNERABLE_LOW = 1

SCORE_LIFE_THREAT = 3
SCORE_TIME_CRITICAL = 2
SCORE_SPREADING_HAZARD = 1

SCORE_UNCERTAINTY_PENALTY = 1

SEVERITY_MIN = 1
SEVERITY_MAX = 10


def calculate_severity(incident: Incident) -> int:
    """Calculate deterministic severity score from 1–10.

    Every input factor and its weight is documented at module level.
    The function is deterministic: same inputs always produce the same score.
    """
    score = 1  # base score

    # People affected
    if incident.people_affected > PEOPLE_AFFECTED_HIGH_THRESHOLD:
        score += SCORE_PEOPLE_AFFECTED_HIGH
    elif incident.people_affected > PEOPLE_AFFECTED_MED_THRESHOLD:
        score += SCORE_PEOPLE_AFFECTED_MED
    elif incident.people_affected > 0:
        score += SCORE_PEOPLE_AFFECTED_LOW

    # People trapped
    if incident.people_trapped > PEOPLE_TRAPPED_HIGH_THRESHOLD:
        score += SCORE_PEOPLE_TRAPPED_HIGH
    elif incident.people_trapped > 0:
        score += SCORE_PEOPLE_TRAPPED_LOW

    # Vulnerable people
    if incident.vulnerable_people > VULNERABLE_HIGH_THRESHOLD:
        score += SCORE_VULNERABLE_HIGH
    elif incident.vulnerable_people > 0:
        score += SCORE_VULNERABLE_LOW

    # Boolean factors
    if incident.life_threat:
        score += SCORE_LIFE_THREAT
    if incident.time_critical:
        score += SCORE_TIME_CRITICAL
    if incident.spreading_hazard:
        score += SCORE_SPREADING_HAZARD

    # Uncertainty penalty: if ALL numeric fields are zero, assume missing data
    all_zero = (
        incident.people_affected == 0
        and incident.people_trapped == 0
        and incident.vulnerable_people == 0
    )
    if all_zero:
        score += SCORE_UNCERTAINTY_PENALTY

    return max(SEVERITY_MIN, min(SEVERITY_MAX, score))


def get_urgency(severity: int) -> UrgencyLevel:
    """Map severity score to urgency band."""
    if severity <= 3:
        return UrgencyLevel.LOW
    elif severity <= 6:
        return UrgencyLevel.MEDIUM
    elif severity <= 8:
        return UrgencyLevel.HIGH
    else:
        return UrgencyLevel.CRITICAL


def assess_incident(incident: Incident) -> Incident:
    """Calculate and attach severity + urgency to an incident."""
    incident.severity = calculate_severity(incident)
    incident.urgency = get_urgency(incident.severity)
    return incident
