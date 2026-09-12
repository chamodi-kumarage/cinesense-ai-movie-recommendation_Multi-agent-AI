import json
from pathlib import Path
from app.agents.comparison import ComparisonExplainabilityAgent, MODE_WEIGHTS


def _movies():
    return [
        {'id':1,'title':'Chef','year':2014,'poster_url':'','moods':['Happy','Relaxed'],'genres':['Comedy','Drama'],'runtime':114,'rating':7.1,'pace':'Gentle','language':'English'},
        {'id':2,'title':'Inception','year':2010,'poster_url':'','moods':['Tense','Exciting'],'genres':['Action','Science Fiction'],'runtime':148,'rating':8.1,'pace':'Fast','language':'English'},
        {'id':3,'title':'A Quiet Place','year':2018,'poster_url':'','moods':['Thrilled'],'genres':['Horror','Thriller'],'runtime':90,'rating':7.4,'pace':'Intense','language':'English'},
    ]


def test_step9_has_six_decision_modes():
    assert set(MODE_WEIGHTS) == {'best_mood','best_quality','shortest','most_exciting','safest_group','different'}


def test_step9_scoring_returns_risk_and_six_criteria():
    agent=ComparisonExplainabilityAgent()
    rows,_=agent._score_rows(_movies(),'Relaxed','best_mood',120,{'preferred_genres':['Comedy'],'disliked_genres':['Horror'],'history_genres':['Comedy'],'preferred_language':'English'}, {})
    assert len(rows)==3
    for row in rows:
        for key in ['overall_score','mood_fit','genre_fit','time_fit','rating_fit','pace_fit','history_fit','risk_level','risk_score','risk_reasons']:
            assert key in row


def test_step9_remove_horror_penalises_horror():
    agent=ComparisonExplainabilityAgent()
    rows,_=agent._score_rows(_movies(),'Relaxed','best_mood',120,{}, {'remove_genre':'Horror'})
    horror=next(r for r in rows if r['title']=='A Quiet Place')
    assert horror['overall_score'] < 50


def test_step9_seed_contains_360_movies():
    path=Path(__file__).resolve().parents[1]/'data'/'movies_seed.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    assert len(data)==360
    assert len({m['tmdb_id'] for m in data})==360
