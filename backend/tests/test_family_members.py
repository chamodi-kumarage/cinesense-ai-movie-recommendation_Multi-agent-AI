from test_watch_insights import history
from app.dependencies import get_current_user
from app.main import app
from app.models import User
from app.security import encrypt_text


def test_household_lists_owner_and_accepted_member(history):
    client, Session, owner, _, _ = history
    response = client.get('/api/family/household')
    assert response.status_code == 200
    home = response.json()
    assert len(home['members']) == len(home['participants']) == 1
    assert home['members'][0]['email'] == owner.email
    assert home['participants'][0]['id'] == home['members'][0]['profile_id']
    with Session() as db:
        member = User(email='member@example.com', password_hash='fixture', plan='free', consented=True, display_name_enc=encrypt_text('Family Member'))
        db.add(member); db.commit()
    invite = client.post('/api/family/invites', json={'email':member.email,'role':'member'})
    assert invite.status_code == 200
    assert len(client.get('/api/family/household').json()['pending_invites']) == 1
    app.dependency_overrides[get_current_user] = lambda: member
    assert client.post('/api/family/invites/accept', json={'token':invite.json()['token']}).status_code == 200
    home = client.get('/api/family/household').json()
    assert len(home['members']) == len(home['participants']) == 2
    assert home['pending_invites'] == []
    assert home['current_role'] == 'member' and not home['can_manage']
    assert any(p['name'] == 'Family Member' for p in home['participants'])
    assert client.get('/api/family/members').json()['members'] == home['members']


def test_private_profiles_vote_and_update_one_vote(history):
    import json
    from app.models import GroupSession
    client, Session, _, first, second = history
    created = client.post('/api/family/groups', json={'profile_ids':[first.id,second.id], 'free_minutes':180})
    assert created.status_code == 200
    sid = created.json()['session_id']
    with Session() as db:
        row = db.get(GroupSession, sid)
        row.candidate_scores_json = json.dumps({'1':{'group_score':80},'2':{'group_score':70}})
        db.commit()
    for pid, mid in [(first.id,1),(second.id,2),(first.id,2)]:
        response = client.post(f'/api/family/groups/{sid}/vote', json={'profile_id':pid,'movie_id':mid})
        assert response.status_code == 200
    result = client.get(f'/api/family/groups/{sid}/result').json()
    assert result['votes_cast'] == 2
    assert result['winner']['movie_id'] == 2 and result['winner']['votes'] == 2

