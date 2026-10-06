import pytest
from test_watch_insights import history
from app.agents.mood import MoodPreferenceAgent
from app.protocol import AgentEnvelope


@pytest.mark.parametrize('text', [
    'I do not feel sad', 'I am not sad', "I don't feel sad",
    'I am not feeling particularly sad', 'I never feel sad',
    'I do not really want to feel sad', 'I am not happy',
])
def test_extended_negation_does_not_assign_an_emotion(history, text):
    _, Session, _, _, _ = history
    with Session() as db:
        result = MoodPreferenceAgent().analyze(db, AgentEnvelope(trace_id='negation',sender='test',receiver='mood_preference',intent='test',payload={}), text)
    assert result['mood'] is None
    assert result['detected_moods'] == []


@pytest.mark.parametrize('text, expected', [
    ('I do not feel sad but I feel happy', 'Happy'),
    ('I am not tired. I feel sad', 'Sad/Cathartic'),
    ('I was not sad yesterday but I feel sad now', 'Sad/Cathartic'),
    ('I feel sad', 'Sad/Cathartic'),
    ('I do not feel happy but I am sad', 'Sad/Cathartic'),
])
def test_negation_preserves_positive_and_new_clause_emotions(history, text, expected):
    _, Session, _, _, _ = history
    with Session() as db:
        result = MoodPreferenceAgent().analyze(db, AgentEnvelope(trace_id='positive',sender='test',receiver='mood_preference',intent='test',payload={}), text)
    assert result['mood'] == expected


def test_negated_checkin_asks_user_to_choose_and_respects_override(history):
    client, _, _, _, _ = history
    result = client.post('/api/planner/mood-check', json={'text':'I do not feel sad'}).json()
    assert result['mood'] is None and result['detected_moods'] == []
    assert not result['confirmed'] and 'Choose the mood' in result['message']
    manual = client.post('/api/planner/mood-check', json={'text':'I do not feel sad','selected_mood':'Happy'}).json()
    assert manual['mood'] == 'Happy' and manual['confirmed']
