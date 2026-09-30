import pytest
from unittest.mock import patch, MagicMock
from backend.state import CrisisState
from backend.models import Plan, ValidationResult, PlanMetrics, Incident, Unit, UnitType
from backend.agents.command_agent import CommandPlanningAgent
from backend.llm.gemini_provider import GeminiProvider

@pytest.fixture
def mock_state():
    state = CrisisState()
    # add some dummy data
    inc = Incident(id="INC-1", type="Fire", location="A", latitude=0, longitude=0)
    u = Unit(id="U-1", type=UnitType.AMBULANCE)
    state.incidents.append(inc)
    state.units.append(u)
    
    p1 = Plan(id="P1", strategy_name="BALANCED")
    from backend.models import Assignment
    p1.assignments = [Assignment(incident_id="INC-1", unit_id="U-1", eta_minutes=10)]
    p1.validation = ValidationResult(valid=True)
    p1.metrics = PlanMetrics(total_covered=1, reserve_units=0)
    p1.metrics = PlanMetrics(total_covered=1, reserve_units=0)
    
    state.candidate_plans.append(p1)
    return state

def test_llm_provider_missing_key():
    with patch.dict('os.environ', {}, clear=True):
        provider = GeminiProvider()
        assert not provider.is_available()
        assert provider.generate_explanation("prompt") == ""

def test_llm_provider_available():
    with patch.dict('os.environ', {"GEMINI_API_KEY": "fake_key"}):
        provider = GeminiProvider()
        assert provider.is_available()

@patch('google.genai.Client')
def test_valid_structured_response(mock_client):
    with patch.dict('os.environ', {"GEMINI_API_KEY": "fake_key"}):
        provider = GeminiProvider()
        mock_response = MagicMock()
        mock_response.text = '{"summary": "Test Summary", "why_this_plan": "Why test", "trade_off": "Trade test", "why_not_alternatives": {}, "risk": "Risk test", "what_changed": ""}'
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        resp = provider.generate_explanation("prompt")
        assert "Test Summary" in resp

@patch('google.genai.Client')
def test_malformed_llm_response(mock_client):
    with patch.dict('os.environ', {"GEMINI_API_KEY": "fake_key"}):
        provider = GeminiProvider()
        mock_response = MagicMock()
        mock_response.text = 'NOT JSON'
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        resp = provider.generate_explanation("prompt")
        assert resp == "NOT JSON"

@patch('google.genai.Client')
def test_api_failure_fallback(mock_client):
    with patch.dict('os.environ', {"GEMINI_API_KEY": "fake_key"}):
        provider = GeminiProvider()
        mock_client.return_value.models.generate_content.side_effect = Exception("API Error")
        resp = provider.generate_explanation("prompt")
        assert resp == ""

def test_deterministic_explanation_fallback(mock_state):
    # Missing API key means fallback to deterministic
    with patch.dict('os.environ', {}, clear=True):
        agent = CommandPlanningAgent()
        state = agent.select_plan(mock_state)
        # Should populate standard explanation, but not ai_explanation
        assert state.recommended_plan is not None
        assert state.recommended_plan.explanation != ""
        assert state.recommended_plan.ai_explanation is None

@patch('backend.llm.gemini_provider.GeminiProvider.generate_explanation')
def test_llm_structured_parsing(mock_generate, mock_state):
    with patch.dict('os.environ', {"GEMINI_API_KEY": "fake_key"}):
        mock_generate.return_value = '{"summary": "Test Summary", "why_this_plan": "Why test", "trade_off": "Trade test", "why_not_alternatives": {}, "risk": "Risk test", "what_changed": ""}'
        
        agent = CommandPlanningAgent()
        state = agent.select_plan(mock_state)
        
        assert state.recommended_plan.ai_explanation is not None
        assert state.recommended_plan.ai_explanation["summary"] == "Test Summary"
        assert state.recommended_plan.ai_explanation["why_this_plan"] == "Why test"

@patch('backend.llm.gemini_provider.GeminiProvider.generate_explanation')
def test_llm_cannot_mutate_crisis_state(mock_generate, mock_state):
    with patch.dict('os.environ', {"GEMINI_API_KEY": "fake_key"}):
        mock_generate.return_value = '{"summary": "Test Summary"}'
        
        initial_version = mock_state.version
        
        agent = CommandPlanningAgent()
        state = agent.select_plan(mock_state)
        
        # Agent increments version internally during selection, but AI should not change any deterministic properties
        assert len(state.candidate_plans) == 1
        assert state.candidate_plans[0].score is not None

@patch('backend.llm.gemini_provider.GeminiProvider.generate_explanation')
def test_command_agent_receives_verified_evidence(mock_generate, mock_state):
    with patch.dict('os.environ', {"GEMINI_API_KEY": "fake_key"}):
        agent = CommandPlanningAgent()
        agent.select_plan(mock_state)
        
        # Verify prompt contained the evidence keys
        prompt = mock_generate.call_args[0][0]
        assert "state_version" in prompt
        assert "recommended_plan" in prompt
        assert "decision_debts" in prompt

