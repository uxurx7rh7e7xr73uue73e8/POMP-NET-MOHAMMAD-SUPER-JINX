import os
import pytest

os.environ['ADMIN_USERNAME'] = 'testadmin'
os.environ['ADMIN_PASSWORD'] = 'Correct-Horse-Battery-42!'
os.environ['SESSION_SECRET'] = 'test-session-secret-which-is-longer-than-thirty-two-bytes'
os.environ['DATA_DIR'] = os.path.join(os.path.dirname(__file__), '.testdata')

from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    with TestClient(app, base_url='https://testserver') as c:
        yield c

def test_health_is_public(client):
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'

def test_login_account_create_list_toggle_and_logout(client):
    assert client.get('/').status_code == 200
    bad = client.post('/login', data={'username':'wrong','password':'wrong'})
    assert bad.status_code == 401
    login = client.post('/login', data={'username':'testadmin','password':'Correct-Horse-Battery-42!'}, follow_redirects=False)
    assert login.status_code == 303
    assert client.get('/').status_code == 200
    created = client.post('/accounts', data={'username':'sample-user','quota':'12.5','expires':'2030-01-01','note':'test'}, follow_redirects=False)
    assert created.status_code == 303
    items = client.get('/api/accounts').json()
    assert len(items) == 1
    assert items[0]['username'] == 'sample-user'
    assert items[0]['quota_gb'] == 12.5
    assert items[0]['status'] == 'active'
    assert len(items[0]['public_id']) == 36
    public_page = client.get('/sub/' + items[0]['public_id'])
    assert public_page.status_code == 200
    assert 'اطلاعات اشتراک' in public_page.text
    renewed = client.post('/accounts/1/renew', data={'expires':'2031-05-10'}, follow_redirects=False)
    assert renewed.status_code == 303
    assert client.get('/sub/' + items[0]['public_id']).status_code == 200
    toggled = client.post('/accounts/1/toggle', follow_redirects=False)
    assert toggled.status_code == 303
    assert client.get('/api/accounts').json()[0]['status'] == 'suspended'
    client.get('/logout', follow_redirects=False)
    assert client.get('/api/accounts').status_code == 401
