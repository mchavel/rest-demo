from typing import Any
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


class DBFactory:
    
    @staticmethod
    def getDBType(type: str) -> Any:
        if type.upper() == 'MOCK':
            return DBMock()
        elif type.upper() == 'MONGO':
            return DBMongo()
        else:
            raise ValueError("Invalid DB Type")


class DB:
    pass


class DBMock(DB):

    def __init__(self) -> None:
        self._data = {}
        self._reloads = 0
        self._id = 10000
        log.info(f'Using internal mock DB.')  

    def __str__(self) -> str:
        return "Mock DB (non-persistent internal memory)"    
    
    def set_non_string_fields(self, field_types: dict[str, str]) -> None:
        self.field_types = field_types    

    def reloaddata(self, datafile: str) -> None:
        self._data = {}
        self._reloads += 1  # track data reloads
        try:
            with open(datafile, 'r') as file:
                for line in file:
                    jsonobj = json.loads(line)
                    jsonobj.pop('_id', None)
                    self.create(jsonobj)
            log.info(f'Loaded demo data from file: {datafile}')
        except Exception as err:
            log.error(f'Unable to load demo data file: {datafile}', exc_info=True)

    def num_data_reloads(self) -> int:
        return self._reloads
    
    # number of objects 
    def objcount(self) -> int:
        return len(self._data)

    # list of object ids
    def id_list(self) -> list[str]:
        return list(map(lambda x: str(x['_id']) , self._data))
 
    def _next_id(self) -> str:
        self._id += 1
        return str(self._id)

    # check for valid id
    @staticmethod
    def valid_id(id) -> bool:
        if (id.isdigit()):
            return True
        else:
            return False

    # convert fields to proper db type
    @staticmethod
    def _fix_input_types(map, field_types) -> None:
        if 'id' in map: 
            map['_id'] = map['id']
            del map['id']
        for field in map.keys():
            if (field == '_id'):
                map[field] = str(map[field])
            if field in field_types:
                if field_types[field] == 'INT':
                    map[field] = int(map[field])
                elif field_types[field] == 'DATE':
                    map[field] = datetime.fromisoformat(parse(map[field]).strftime('%Y-%m-%dT%H:%M:%S'))
        

    ### Mock DB CRUD Operations ###

    def get(self, id: str) -> Any:
        if id in self._data:
            obj = self._data.get(id)
            obj['_id'] = id
            return obj
        else:
            return None

    def create(self, values: dict[str, str]) -> str:
        DBMock._fix_input_types(values, self.field_types)
        id = self._next_id()
        self._data[id] = values
        return id
    
    def search(self, filter: dict[str, str], sort_field: str, skip: int, limit: int) -> list[Any]:
        """ Returns all data. Filter not implimented for mock DB."""
        DBMock._fix_input_types(filter, self.field_types)
        result = []
        for id, obj in sorted(self._data.items(), key=lambda x: x[1][sort_field]):
            obj['_id'] = id
            result.append(obj)
        if limit > 0:
            return result[skip:(skip+limit)]
        else:
            return result[skip:]


    def update(self, id: str, values: dict[str, str]) -> int:
        DBMock._fix_input_types(values, self.field_types)
        if id in self._data:
            obj = self._data.get(id)
            for k in values:
                obj[k] = values[k]
            self._data[id] = obj    
            return 1
        else:
            return 0
        
    def replace(self, id: str, values: dict[str, str]) -> int:
        DBMock._fix_input_types(values, self.field_types)
        if id in self._data:
            self._data[id] = values
            return 1
        else:
            return 0

    def delete(self, id: str) -> int:
        if id in self._data:
            self._data.pop(id)
            return 1
        else:
            return 0



class DBMongo(DB):

    def __init__(self) -> None:
        self.config()
        self.connect()
        self.db = self.client.get_database(self.dbname)  # db handle
        self.coll = self.db[self.collname]               # collection handle
        self.field_types: dict[str, str] = {}  # dict of non string field types 

    def __str__(self) -> str:
        return f"Mongo DB ({self.host}:{self.port})"    

    def config(self) -> None:          
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

    def connect(self) -> None:
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

    def set_non_string_fields(self, field_types: dict[str, str]) -> None:
        self.field_types = field_types    


    # reload sample data
    def reloaddata(self, datafile: str) -> None:
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

    def num_data_reloads(self) -> int:
        return self.db['apistatus'].count_documents({})

    # number of objects 
    def objcount(self) -> int:
        return self.coll.count_documents({})
    
    # list of object ids
    def id_list(self) -> list[str]:
        return list(map(lambda x: str(x['_id']) ,self.coll.find({}, {'_id':1})))

    
    # check for valid Mongo ObjectId
    @staticmethod
    def valid_id(id) -> bool:
        return (ObjectId.is_valid(id))

    
    # convert fields to proper db type
    @staticmethod
    def _fix_input_types(map, field_types) -> None:
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

    def get(self, id: str) -> Any:
        obj = self.coll.find_one({'_id': ObjectId(id)})
        return obj

    def search(self, filter: dict[str, str], sort_field: str, skip: int, limit: int) -> list[Any]:
        DBMongo._fix_input_types(filter, self.field_types)
        results = []
        for obj in self.coll.find(filter).sort(sort_field, 1).skip(skip).limit(limit):
            results.append(obj)
        return results    

    def create(self, values: dict[str, str]) -> str:
        DBMongo._fix_input_types(values, self.field_types)
        id = self.coll.insert_one(values).inserted_id
        return str(id)

    def update(self, id: str, values: dict[str, str]) -> int:
        DBMongo._fix_input_types(values, self.field_types)
        count = self.coll.update_one({'_id': ObjectId(id)}, {"$set": values}).matched_count
        return count

    def replace(self, id: str, values: dict[str, str]) -> int:
        DBMongo._fix_input_types(values, self.field_types)
        count = self.coll.replace_one({'_id': ObjectId(id)}, values).matched_count
        return count

    def delete(self, id: str) -> int:
        count = self.coll.delete_one({'_id': ObjectId(id)}).deleted_count
        return count
