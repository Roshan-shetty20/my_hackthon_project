import os
import json
import pytest
from unittest.mock import patch, MagicMock

from backend.state import CrisisState
from backend.planner import generate_candidate_plans
from backend.comparator import compare_and_select, calculate_decision_debts, calculate_decision_confidence
from backend.agents.command_agent import CommandPlanningAgent
from backend.agents.incident_agent import IncidentAssessmentAgent
from backend.simulator import DeterministicSimulator
from backend.replanner import apply_unit_breakdown, apply_road_block, apply_new_incident
from backend.route import calculate_routes
import os

def _strip_comment(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}

def _load_json(name):
    path = os.path.join(os.path.dirname(__file__), "..", "data", name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def initialize_scenario():
    from backend.models import Incident, Unit, RoadCondition
    incidents = [Incident(**_strip_comment(d)) for d in _load_json("incidents.json")]
    units = [Unit(**_strip_comment(d)) for d in _load_json("units.json")]
    road_conditions = [RoadCondition(**_strip_comment(d)) for d in _load_json("roads.json")]
    
    state = CrisisState(incidents=incidents, units=units, road_conditions=road_conditions)
    
    # Assess incidents
    agent = IncidentAssessmentAgent()
    state = agent.assess_all(state)
    return state

def run_planning_cycle(state):
    state = generate_candidate_plans(state)
    cmd_agent = CommandPlanningAgent()
    state = cmd_agent.select_plan(state)
    state.decision_debts = calculate_decision_debts(state)
    state.decision_confidence = calculate_decision_confidence(state)
    return state

@patch('google.genai.Client')
def test_golden_scenario_full_end_to_end(mock_client):
    with patch.dict('os.environ', {"GEMINI_API_KEY": "fake_key"}):
        # Mock LLM to simulate structured AI explanation
        mock_response = MagicMock()
        mock_response.text = '{"summary": "Golden Plan Summary", "why_this_plan": "Covers critical.", "trade_off": "Lower reserve", "why_not_alternatives": {}, "risk": "Unit SPOF", "what_changed": "Re-routed due to block"}'
        mock_client.return_value.models.generate_content.return_value = mock_response

        # 1. Initialize
        state = initialize_scenario()
        assert len(state.incidents) > 0
        assert len(state.units) > 0
        assert len(state.road_conditions) > 0
        v_initial = state.version

        # 2. Planning (Initial Crisis)
        state = run_planning_cycle(state)
        assert len(state.candidate_plans) > 0
        assert state.recommended_plan is not None
        assert state.recommended_plan.ai_explanation is not None
        assert state.recommended_plan.ai_explanation["summary"] == "Golden Plan Summary"
        v_planned = state.version
        assert v_planned > v_initial
        
        # 3. Simulate Human Dispatch (Select incident & unit & route)
        inc_id = state.incidents[0].id
        unit_id = state.units[0].id
        routes = calculate_routes(state.units[0].latitude, state.units[0].longitude, state.incidents[0].latitude, state.incidents[0].longitude, state.road_conditions)
        assert len(routes) > 0
        fastest_route = routes[0]
        
        state.dispatch_unit(unit_id, inc_id, fastest_route)
        mission = next((m for m in state.active_missions.values() if m.unit_id == unit_id), None)
        assert mission is not None
        assert state.get_unit(unit_id).status.value == "EN_ROUTE"
        v_dispatch = state.version
        assert v_dispatch > v_planned
        
        # 4. Unit Movement
        state.advance_missions(step_percent=50.0)
        assert mission.progress_percent == 50.0
        
        # 5. Simulation Event 1: Weather
        sim = DeterministicSimulator()
        ev1 = sim.next_event()
        assert ev1.event_type == "weather_update"
        
        from backend.state import StateHistory
        from backend.models import Incident, UnitType
        history = StateHistory()
        
        # 6. Simulation Event 2: Road Block
        ev2 = sim.next_event()
        assert ev2.event_type == "road_block"
        road_id = ev2.payload["road_id"]
        state = apply_road_block(state, history, road_id)
        
        # The block should trigger reroute/interruption and state mutation
        v_blocked = state.version
        assert v_blocked > v_dispatch
        road = next((r for r in state.road_conditions if r.id == road_id), None)
        assert road is not None
        assert road.blocked is True
        
        # 7. Simulation Event 3: Unit Breakdown
        ev3 = sim.next_event()
        assert ev3.event_type == "unit_failure"
        failed_unit_id = ev3.payload["unit_id"]
        
        # We manually fail the unit
        state = apply_unit_breakdown(state, history, failed_unit_id)
        v_breakdown = state.version
        assert v_breakdown > v_blocked
        assert state.get_unit(failed_unit_id).status.value == "BROKEN_DOWN"
        
        # After breakdown, replanner automatically kicks in and generates new plans
        assert len(state.plan_diffs) > 0
        
        # 8. Simulation Event 4: New Incident
        ev4 = sim.next_event()
        assert ev4.event_type == "new_incident"
        payload = ev4.payload
        new_inc = Incident(
            id=payload["incident_id"],
            type=payload["type"],
            location=ev4.location,
            latitude=0.0,
            longitude=0.0,
            severity=payload["severity"],
            people_affected=payload["people_affected"]
        )
        state = apply_new_incident(state, history, new_inc)
        v_new_incident = state.version
        assert v_new_incident > v_breakdown
        
        # 9. Verify Action Log contains the full sequence
        actions = [log.action.upper() for log in state.action_log]
        assert any("RECOMMENDED" in a for a in actions)
        assert any("DISPATCH" in a for a in actions)
        assert any("BLOCK" in a for a in actions)
        assert any("BREAKDOWN" in a for a in actions)
        
        # 10. Verify Decision Debt and Resilience are calculated
        assert state.recommended_plan.metrics is not None
        assert state.recommended_plan.metrics.resilience_score > 0
        
        # Verify Plan Diff exists
        assert len(state.plan_diffs) > 0
        diff = state.plan_diffs[-1]
        assert hasattr(diff, 'added_assignments')
        
def test_golden_scenario_degraded_mode():
    with patch.dict('os.environ', {}, clear=True):
        state = initialize_scenario()
        state = run_planning_cycle(state)
        
        # The deterministic template should work perfectly, but ai_explanation is None
        assert state.recommended_plan is not None
        assert state.recommended_plan.explanation != ""
        assert state.recommended_plan.ai_explanation is None
        
        inc_id = state.incidents[0].id
        unit_id = state.units[0].id
        routes = calculate_routes(state.units[0].latitude, state.units[0].longitude, state.incidents[0].latitude, state.incidents[0].longitude, state.road_conditions)
        fastest_route = routes[0]
        
        state.dispatch_unit(unit_id, inc_id, fastest_route)
        assert state.get_unit(unit_id).status.value == "EN_ROUTE"
        
        # System continues normally
        state.advance_missions(step_percent=100.0)
        assert state.get_unit(unit_id).status.value == "ON_SCENE"
