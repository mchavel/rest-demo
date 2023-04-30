from pymongo import MongoClient
from bson.objectid import ObjectId 
from datetime import datetime
from dateutil.parser import parse
from flask.logging import default_handler
import logging
import json
import os
import configparser
import base64

# Set logger
log = logging.getLogger()
log.addHandler(default_handler)


class DB:
    pass


class DBMongo(DB):

    def __init__(self):
        self.config()
        self.connect()
        self.db = self.client.get_database(self.dbname)  # db handle
        self.coll = self.db[self.collname]               # collection handle
        self.field_types = {}  # dict of non string field types 

    def config(self):          
        # Parse config file
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.host = config['mongo']['host']
        self.port = int(config['mongo']['port'])
        self.user = base64.b64decode(config['mongo']['username']).decode("utf-8").strip()
        self.pwd  = base64.b64decode(config['mongo']['password']).decode("utf-8").strip()
        self.dbname = config['mongo']['database']
        self.collname    = config['mongo']['collection']

        # Override Mongo hostname & port if set via env variables 
        # (convenient for running inside a container)
        if os.environ.get('MONGO_HOST') is not None:
            self.host = os.environ.get('MONGO_HOST')
        if os.environ.get('MONGO_PORT') is not None:
            self.port= int(os.environ.get('MONGO_PORT'))

    def connect(self):
        try: 
            self.client = MongoClient(host=self.host,
                                    port=self.port,
                                    username=self.user,
                                    password=self.pwd,
                                    serverSelectionTimeoutMS=10000)
            self.dbinfo = self.client.server_info()
            log.info(f'Connected to Mongo DB: {self.host}:{self.port}')   
        except Exception as err:
            log.error(f'ERROR: Unable to connect to Mongo DB: {self.host}:{self.port}')
            raise err

    def set_non_string_fields(self, field_types):
        self.field_types = field_types    


    # reload sample data
    def reloaddata(self, datafile):
        self.coll.drop()
        self.db['apistatus'].insert_one({'reload': 1, 'ts': datetime.utcnow()})  # track data reloads in db
        try:
            with open(datafile, 'r') as file:
                for line in file:
                    jsonobj = json.loads(line)
                    jsonobj.pop('_id', None)
                    self.coll.insert_one(jsonobj)
            log.info(f'Loaded demo data from file: {datafile}')
        except Exception as err:
            log.error(f'Unable to load demo data file: {datafile}', exc_info=True)

    def num_data_reloads(self):
        return self.db['apistatus'].count_documents({})

    # number of objects 
    def objcount(self):
        return self.coll.count_documents({})
    
    # list of object ids (tyepe string)
    def id_list(self):
        return map(lambda x: str(x['_id']) ,self.coll.find({}, {'_id':1}))

    
    # check for valid Mongo ObjectId
    @staticmethod
    def valid_id(id):
        return (ObjectId.is_valid(id))


    # convert fields to proper db type
    def _fix_input_types(map, field_types):
        if 'id' in map: 
            map['_id'] = map['id']
            del map['id']
        for field in map.keys():
            if (field == '_id'):
                map[field] = ObjectId(map[field])
            if field in field_types:
                if field_types[field] == 'INT':
                    map[field] = int(map[field])
                elif field_types[field] == 'DATE':
                    map[field] = datetime.fromisoformat(parse(map[field]).strftime('%Y-%m-%dT%H:%M:%S'))
        

    ### Mongo DB CRUD Operations ###

    def get(self, id):
        obj = self.coll.find_one({'_id': ObjectId(id)})
        return obj

    def search(self, mapping, sort_field, skip, limit):
        DBMongo._fix_input_types(mapping, self.field_types)
        results = []
        for obj in self.coll.find(mapping).sort(sort_field, 1).skip(skip).limit(limit):
            results.append(obj)
        return results    

    def create(self, obj):
        DBMongo._fix_input_types(obj, self.field_types)
        id = self.coll.insert_one(obj).inserted_id
        return id

    def update(self, id, mapping):
        DBMongo._fix_input_types(mapping, self.field_types)
        count = self.coll.update_one({'_id': ObjectId(id)}, {"$set": mapping}).matched_count
        return count

    def replace(self, id, mapping):
        DBMongo._fix_input_types(mapping, self.field_types)
        count = self.coll.replace_one({'_id': ObjectId(id)}, mapping).matched_count
        return count

    def delete(self, id):
        count = self.coll.delete_one({'_id': ObjectId(id)}).deleted_count
        return count
