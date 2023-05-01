from locust import HttpUser, task, between
from api_db import DBMongo
import random


class APIUser(HttpUser):

    # Default host
    host = 'http://localhost:5000'

    # Get album ids from db
    db = DBMongo()
    idlist = list(db.id_list())

    # Wait time
    wait_min = 3
    wait_max = 20
    wait_time = between(wait_min, wait_max)

    # Task weights
    wt_list         = 1
    wt_searchyear   = 3
    wt_searchlabel  = 4
    wt_get          = 2
    wt_create       = 2
    wt_update       = 1


    ### Tasks ###
    @task(wt_list)
    def list_albums(self):
        with self.client.get(name='GetAll', 
                             url='/albums', 
                             catch_response=True) as response:
            code = response.status_code
            if code == 200:
                response.success()
            else:
                response.failure('Response code:', code)     

    @task(wt_searchyear)
    def search_albums_by_year(self):
        i = random.randint(0,6)
        year = [1966, 1967, 1968, 1969, 1970, 1971, 1072]
        with self.client.get(name='SearchByYear', 
                             url='/albums',
                             params={'year': year[i]}, 
                             catch_response=True) as response:
            code = response.status_code
            if code == 200:
                response.success()
            else:
                response.failure('Response code:', code)


    @task(wt_searchlabel)
    def search_albums_by_artist(self):
        i = random.randint(0,1)
        label = ['Columbia', 'Atlantic', 'Reprise', 'Decca']
        with self.client.get(name='SearchByLabel', 
                             url='/albums',
                             params={'artist': label[i]}, 
                             catch_response=True) as response:
            code = response.status_code
            if code == 200:
                response.success()
            else:
                response.failure('Response code:', code)

    @task(wt_get)
    def get_album(self):
        i = random.randint(0,50)
        with self.client.get(name='GetById', 
                             url='/albums/' + APIUser.idlist[i], 
                             catch_response=True) as response:
            code = response.status_code
            if code == 200:
                response.success()
            else:
                response.failure(f'Response code: {code}')


    @task(wt_create)
    def create_album(self):
        with self.client.post(name='Create',
                              url='/albums',
                              data={'title': 'LocustTitle', 'artist': 'LocustArtist', 'label': 'LocustCreated'}, 
                              catch_response=True) as response:
            code = response.status_code
            #print(code)
            #print(response.headers)
            #print(response.text)
            if code == 201:
                newid = response.json()['_id']
                response.success()
            else:
                response.failure(f'Response code: {code}')

    @task(wt_update)
    def update_album(self):
        i = random.randint(0,50)
        with self.client.patch(name='Update', 
                               url='/albums/' + APIUser.idlist[i],
                               data={'label': 'LocustUpdated'}, 
                               catch_response=True) as response:
            code = response.status_code
            if code == 200:
                response.success()
            else:
                response.failure(f'Response code: {code}')

