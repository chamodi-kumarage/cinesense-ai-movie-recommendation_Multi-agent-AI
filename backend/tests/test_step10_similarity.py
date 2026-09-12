from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Movie, MovieProducer
from app.agents.retrieval import RetrievalRecommendationAgent
from app.agents.comparison import ComparisonExplainabilityAgent
from app.protocol import AgentEnvelope


def _db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _movie(title,year,genres,overview,rating,director,cast,moods='Thrilled',studio='Studio',keywords=''):
    return Movie(title=title,year=year,genres=genres,runtime=110,overview=overview,rating=rating,language='English',studio=studio,director=director,cast=cast,moods=moods,pace='Moderate',keywords=keywords,poster_url='',backdrop_url='')


def test_similarity_actor_director_and_excludes_source():
    db=_db()
    src=_movie('Dream Heist',2010,'Science Fiction|Thriller','A thief enters dreams to plant an idea.',8.1,'Nolan','Leo|Joseph','Thrilled','WB','dream|heist')
    same=_movie('Dream Team',2012,'Science Fiction|Action','A team enters a constructed mind world.',7.8,'Nolan','Leo|Amy','Thrilled','WB','dream|team')
    other=_movie('Quiet Dinner',2011,'Drama','A family has dinner and talks.',7.2,'Other','Sam|Pat','Relaxed','Indie','family')
    db.add_all([src,same,other]);db.commit()
    agent=RetrievalRecommendationAgent()
    env=AgentEnvelope(trace_id='s1',sender='orchestrator',receiver='retrieval',intent='find_similar',payload={})
    result=agent.find_similar(db,env,src.id,{'modes':['cast','director'],'weights':{'cast':60,'director':40},'limit':5})
    assert result['results'][0]['id']==same.id
    assert all(x['id']!=src.id for x in result['results'])
    assert result['results'][0]['components']['director']==100.0
    assert result['results'][0]['matches']['actors']==['Leo']


def test_similarity_year_and_required_genre_filter():
    db=_db()
    src=_movie('Origin',2010,'Science Fiction|Thriller','A complex science fiction mystery.',8.0,'A','One')
    near=_movie('Near',2012,'Thriller|Mystery','Another science fiction mystery.',7.0,'B','Two')
    far=_movie('Far',1990,'Comedy','A comedy.',8.5,'C','Three')
    db.add_all([src,near,far]);db.commit()
    agent=RetrievalRecommendationAgent();env=AgentEnvelope(trace_id='s2',sender='orchestrator',receiver='retrieval',intent='find_similar',payload={})
    result=agent.find_similar(db,env,src.id,{'modes':['year','genre'],'preset':'era','required_genre':'Thriller','year_mode':'within_3','limit':5})
    assert [x['id'] for x in result['results']]==[near.id]
    assert result['results'][0]['year_difference']==2


def test_similarity_producer_data_and_explanation():
    db=_db()
    src=_movie('One',2015,'Drama','Shared story about resilience.',7.5,'A','X')
    cand=_movie('Two',2016,'Drama','Shared story about resilience and hope.',7.6,'B','Y')
    db.add_all([src,cand]);db.commit()
    db.add_all([MovieProducer(movie_id=src.id,producer_name='Producer P'),MovieProducer(movie_id=cand.id,producer_name='Producer P')]);db.commit()
    retrieval=RetrievalRecommendationAgent();env=AgentEnvelope(trace_id='s3',sender='orchestrator',receiver='retrieval',intent='find_similar',payload={})
    result=retrieval.find_similar(db,env,src.id,{'modes':['producer','story'],'weights':{'producer':70,'story':30},'limit':5})
    assert result['producer_data_available'] is True
    assert result['results'][0]['components']['producer']==100.0
    explained=ComparisonExplainabilityAgent().explain_similarity(db,AgentEnvelope(trace_id='s4',sender='orchestrator',receiver='comparison',intent='explain_similarity',payload={}),result['source'],result['results'],['producer','story'])
    assert 'shared producer' in explained[0]['why_similar'].lower()


def test_custom_weights_normalize_to_100_percent():
    db=_db();a=_movie('A',2000,'Drama','alpha beta',7,'D','A');b=_movie('B',2001,'Drama','alpha beta',8,'D','A');db.add_all([a,b]);db.commit()
    agent=RetrievalRecommendationAgent();env=AgentEnvelope(trace_id='s5',sender='orchestrator',receiver='retrieval',intent='find_similar',payload={})
    result=agent.find_similar(db,env,a.id,{'modes':['story','genre'],'weights':{'story':40,'genre':20},'limit':3})
    assert round(sum(result['weights'].values()),1)==100.0
