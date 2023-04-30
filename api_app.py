from api_db import DBMongo
from flask import Flask, jsonify, request
from logging.config import dictConfig
from bson.objectid import ObjectId 
from datetime import datetime
from random import randint
from time import sleep
import json
import os
import configparser


# Parse config file
config = configparser.ConfigParser()
config.read('config.ini')
flasklisten = config['flask']['listen_ip']
flaskport = int(config['flask']['port'])
# Configure API object schema (enforced only by this app, not in db)
primaryroute = '/' + config['api']['route']
fields_required = config['api']['required_fields'].split(',')
fields_optional = config['api']['optional_fields'].split(',')
fields_allowed = fields_required + fields_optional
params_allowed = fields_allowed + ['skip', 'limit', 'page']  # additional GET parameters to limit & page thru results
# fields assumed to be of type string unless discovered differently below
int_fields = config['api']['integer_fields'].split(',')
date_fields = config['api']['date_fields'].split(',')
field_types = {}       # dict of non string type fields
for f in int_fields: field_types[f] = 'INT'
for f in date_fields: field_types[f] = 'DATE'
sort_field = config['api']['sortby']

# locate path of demo data file
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
demodata_filename = config['api']['demodatafile']
demodatafile = os.path.join(__location__, demodata_filename)


# Exceptions
class APIError(Exception):
    code = 400
    description = "API Error"

class APIAuthError(APIError):
    code = 403
    description = "Authentication Error"

class APIMethodError(APIError):
    code = 400
    description = "Invalid API Operation"

class APIObjectError(APIError):
    code = 400
    description = "Invalid API Object"

# Custom log config
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

# Custom Flask encoder
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%S')
        return super(MyEncoder, self).default(obj) 

# Flask app config
app = Flask(__name__)
app.json_encoder = MyEncoder
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Flask app error handler
@app.errorhandler(APIError)
def handle_exception(err):
    """Return custom JSON when APIError is raised"""
    response = {"error": err.description, "message": ""}
    if len(err.args) > 0:
        response["message"] = err.args[0]
    return jsonify(response), err.code          

# Instantiate db helper instance
db = DBMongo()
db.set_non_string_fields(field_types)


# Load sample data to a fresh db
# insert random sleep to prevent multiple instances 
# from attempting to reload data at the same time
sleep(randint(0,3000)/1000) 
if db.num_data_reloads() == 0:
    db.reloaddata(demodatafile)

# API Helper Functions
def check_if_allowed(param):
    if param not in params_allowed:
        raise APIObjectError('Unknown paramater: ' + param)  

def check_for_required_fields(map, fields_required):
    for req in fields_required:
        if req not in map:
            raise APIObjectError(req + ' is a required field')   
        


### API Route Handlers ###

# Base landing page
@app.route('/', methods = ['GET'])
def home():
    if request.args.get('reloaddata') == 'true':
       db.reloaddata(demodatafile)
    numrec = db.objcount()
    numreloads = db.num_data_reloads()
    baseurl = request.base_url[:-1]
    html = f"""
<html>
  <body>
    <h1>Album Database API</h1>
        API server connected to Mongo DB: {db.host}:{db.port}<br>
        DB data reloads: {numreloads}<br>
        Entries in DB: {numrec}<br>  
        <p><b>API Base Url:</b> {baseurl}
        <p><b>Routes:</b></br> 
        <table>
        <tr><td>{baseurl+primaryroute}</td><td width=5></td><td>List All or Search (GET), Create (POST)</td></tr>
        <tr><td>{baseurl+primaryroute+'/{id}'}</td width=5><td></td><td>Get (GET), Delete (DELETE), Replace (PUT), Update (PATCH)</td></tr>
        </table>
        <p>
        <b>Fields:</b><br>
"""
    for field in fields_allowed:
        if field in fields_required:
            html += f'{field} (required)<br>'
        else:
            html += f'{field} <br>'
    html += '</body></html>'
    return html


# GET (with search filters)
@app.route(primaryroute, methods = ['GET'])  
def primarysearch():
    filter = {}
    for k in request.args: 
        filter[k] = request.args[k]
        check_if_allowed(k)
    skip = int(filter.pop('skip', 0))
    limit = int(filter.pop('limit', 0))
    if 'page' in filter:  # if page parameter present, ignore the skip parameter
        page = int(filter.pop('page'))
        skip = page * limit 
    data = db.search(filter, sort_field, skip, limit)
    for x in data:  # add path to each object
        x.update({'_href': request.base_url+'/'+str(x['_id'])})
    return jsonify(data)

# GET ONE by id 
@app.route(primaryroute+'/<id>', methods = ['GET'])
def primaryget(id):
    if not DBMongo.valid_id(id):
        return jsonify({'Invalid id': id}), 400
    data = db.get(id)
    if data != None:
        return jsonify(data), 200
    else: 
        return jsonify({}), 404

# CREATE ONE 
@app.route(primaryroute, methods = ['POST'])
def primarycreate():
    myobj = {}
    for k in request.form: 
        myobj[k] = request.form[k]
        check_if_allowed(k)
    check_for_required_fields(myobj, fields_required)
    id = db.create(myobj)
    href = request.base_url + '/' + str(id)
    return jsonify({'Result': 'Object Created', 
                    '_id': id,
                    '_href': href}), 201

# REPLACE ONE by id
@app.route(primaryroute+'/<id>', methods = ['PUT'])
def primaryreplace(id):
    if not DBMongo.valid_id(id):
        return jsonify({'Invalid id': id}), 400
    mappings = {}
    for k in request.form: 
        mappings[k] = request.form[k]
        check_if_allowed(k)
    check_for_required_fields(mappings, fields_required)
    cnt = db.replace(id, mappings)
    href = request.base_url
    return jsonify({'Result': f'{cnt} replaced', '_href': href}), 200
        
# UPDATE ONE by id
@app.route(primaryroute+'/<id>', methods = ['PATCH'])
def primaryupdate(id):
    if not DBMongo.valid_id(id):
        return jsonify({'Invalid id': id}), 400
    mappings = {}
    for k in request.form: 
        mappings[k] = request.form[k]
        check_if_allowed(k)
    cnt = db.update(id, mappings)
    href = request.base_url
    return jsonify({'Result': f'{cnt} updated', '_href': href}), 200

# DELETE ONE by id
@app.route(primaryroute+'/<id>', methods = ['DELETE'])
def primarydelete(id):
    if not DBMongo.valid_id(id):
        return jsonify({'Invalid id': id}), 400
    cnt = db.delete(id)
    if (cnt > 0):
        return jsonify({'Result': f'{cnt} deleted'}), 200
    else:
        return jsonify({'Result': f'{cnt} deleted'}), 404



# Main
if __name__ == '__main__':
    app.run(host=flasklisten, port=flaskport, debug = False)  # start flask app

