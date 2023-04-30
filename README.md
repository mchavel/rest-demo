# restapidemo

## Summary

A Python / Flask application that exposes a simple REST API.  Mongo DB is used for persistent storage.  Out of the box, it is setup as a vinyl record database.  However, the object field names can be easily changed in the python application to represent any simple collection of objects; such as books, employees, etc.     
  

## Usage:

The demo can be deployed as a regular application, via containers or in a Kubernetes cluster.  Specific commands for deploying on Linux are given below.

Once the application is running, point a web browser to http://localhost:5000 to reach the api demo landing page.

Sample data will be automatically loaded from the included albums.json file on startup.  

API Routes are

albums/      - methods GET & POST \
albums/{id}  - methods GET, PUT, PATCH & DELETE 

One can use Postman or any other API test tool to fetch, create and, modify data.
  
  
## Installation:

If the Mongo database is run on the same host as the python application, and the default ports of 27017 and 5000 are free, no configuration changes will be necessary.  Otherwise, edit the mongo hostname and ports as needed in the config.ini file. Or if deploying in containers adjust the host port mappings in the yaml files.

* **Normal Python app** 

  pip install requirements.txt\
  python3 api-app.py


* **Docker Compose:** 

  docker compose -f docker-compose.yaml up 

  The docker-compose.yaml file defines two containers: one for the api server and one for mongo db.  The mongo container uses a docker named volume to persist data between container restarts.


* **Kubernetes cluster:** \
The k8s dir contains manifest files to deploy the flask application and mongo db into a kubernetes cluster.  I have tested deployments on minikube and AWS EKS. Apply the files in the following order:

  kubectl apply -f mongo-secret.yaml \
  kubectl apply -f mongo-db.yaml \
  kubectl apply -f api-app.yaml











