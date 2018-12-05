from pymongo import MongoClient
from bson.objectid import ObjectId
import copy


class MongoHandler():
    def __init__(self, uri, db_name):
        self.uri = uri
        self.db_name = db_name

    def mongo_import(self, json_obj, coll_name = 'train_data'):
        json_obj_copy = copy.deepcopy(json_obj)
        client = MongoClient(self.uri)
        db = client[self.db_name]
        coll = db[coll_name]
        coll.insert_one(json_obj_copy)
        obj_id = str(json_obj_copy['_id'])
        return obj_id

    def mongo_get(self, mongo_id, coll_n='train_data'):
        client = MongoClient(self.uri)
        db = client[self.db_name]
        coll = db[coll_n]
        doc = coll.find_one({"_id": ObjectId(mongo_id)})
        return doc
