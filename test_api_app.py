import requests as req
import pytest


baseurl = 'http://localhost:5000'
endpoint = baseurl + '/albums'


def get_numentries():
    res = req.get(endpoint)
    return len(res.json())

def get_entry(id):
    return req.get(f'{endpoint}/{id}')

def delete_entry(id):
    return req.delete(f'{endpoint}/{id}')

def update_entry(id, fields):
    return req.patch(f'{endpoint}/{id}', fields)

def replace_entry(id, fields):
    return req.put(f'{endpoint}/{id}', fields)


# Sunny Day Tests

def test_baseurl():
    res = req.get(baseurl)
    assert res.status_code == 200

def test_create():
    fields = {'title': 'testtitle', 'artist': 'testartist'}
    res = req.post(endpoint, fields)
    assert res.status_code == 201
    body = res.json()
    id = body['_id']   
    res = get_entry(id)
    assert res.status_code == 200
    entry = res.json()
    assert entry['title'] == 'testtitle'
    assert entry['artist'] == 'testartist'

@pytest.fixture
def new_entry_id():
    fields = {'title': 'testtitle', 'artist': 'testartist'}
    res = req.post(endpoint, fields)
    body = res.json()
    return body['_id']   

def test_replace(new_entry_id):
    id = new_entry_id  
    fields = {'title': 'testtitle', 'artist': 'testartist', 'year': 1999}
    res = replace_entry(id, fields)
    assert res.status_code == 200
    res = get_entry(id)
    assert res.status_code == 200
    entry = res.json()
    assert entry['year'] == 1999

def test_update(new_entry_id):
    id = new_entry_id  
    res = update_entry(id, {'label': 'testlabel'})
    assert res.status_code == 200
    res = get_entry(id)
    assert res.status_code == 200
    entry = res.json()
    assert entry['label'] == 'testlabel'

def test_delete(new_entry_id):
    id = new_entry_id  
    res = delete_entry(id)
    assert res.status_code == 200
    res = get_entry(id)
    assert res.status_code == 404
    
def test_getall():
    res = req.get(endpoint)
    assert res.status_code == 200  
    assert get_numentries() > 0

def test_search():
    pass


# Rainy Day Tests

def test_get_invalid_field():
    fields = {'badfield': 'badboy'}
    res = req.get(endpoint, fields)
    assert res.status_code == 400

def test_create_missing_req_field():
    fields = {'title': 'testtitle', 'year': 2000}
    res = req.post(endpoint, fields)
    assert res.status_code == 400

def test_create_invalid_field():
    fields = {'title': 'testtitle', 'artist': 'testartist', 'badfield': 'badboy'}
    res = req.post(endpoint, fields)
    assert res.status_code == 400

def test_replace_missing_req_field(new_entry_id):
    id = new_entry_id  
    fields = {'title': 'testtitle', 'year': 2000}
    res = replace_entry(id, fields)
    assert res.status_code == 400

def test_replace_invalid_field(new_entry_id):
    id = new_entry_id  
    fields = {'title': 'testtitle', 'artist': 'testartist', 'badfield': 'badboy'}
    res = replace_entry(id, fields)
    assert res.status_code == 400

def test_replace_bad_id():
    id='hdsghgkdhskahkaisbad'
    fields = {'title': 'testtitle', 'artist': 'testartist'}
    res = replace_entry(id, fields)
    assert res.status_code == 400

def test_update_invalid_field(new_entry_id):
    id = new_entry_id  
    fields = {'badfield': 2020}
    res = update_entry(id, fields)
    assert res.status_code == 400

def test_update_bad_id():
    id='hdsghgkisbad'
    fields = {'year': 2023}
    res = update_entry(id, fields)
    assert res.status_code == 400

def test_delete_bad_id():
    id='hdsghgkisbad'
    res = delete_entry(id)
    assert res.status_code == 400

