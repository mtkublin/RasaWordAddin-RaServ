from pymongo import MongoClient
from bson.objectid import ObjectId
import copy

uri = "mongodb://mtkublin:dVyBCQYJkUpFNbph85YLPg54SNa3m4gFnXzq0l8T4GvSVx8QlyZstb1urTKVaOtxoUzT5dLfYQcuQNL6ytNEzA==@mtkublin.documents.azure.com:10255/?ssl=true&replicaSet=globaldb"
db_name = 'train_data_test'


def mongo_import(json_obj, uri = uri, db_name = db_name, coll_name = 'train_data'):

    json_obj_copy = copy.deepcopy(json_obj)

    client = MongoClient(uri)
    db = client[db_name]
    coll = db[coll_name]

    coll.insert_one(json_obj_copy)

    obj_id = str(json_obj_copy['_id'])
    return obj_id

def mongo_get(mongo_id, u=uri, db_n=db_name, coll_n='train_data'):
    client = MongoClient(u)
    db = client[db_n]
    coll = db[coll_n]

    doc = coll.find_one({"_id": ObjectId(mongo_id)})

    return doc