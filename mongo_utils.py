from pymongo import MongoClient
from bson.objectid import ObjectId
import copy


class MongoHandler():
    def __init__(self, uri):
        self.__client = MongoClient(uri)

    def mongo_import(self, json_obj, db_name, coll_name = 'train_data'):
        json_obj_copy = copy.deepcopy(json_obj)
        db = self.__client[db_name]
        coll = db[coll_name]
        coll.insert_one(json_obj_copy)
        obj_id = str(json_obj_copy['_id'])
        return obj_id

    def mongo_get(self, mongo_id, db_name, coll_n='train_data'):
        db = self.__client[db_name]
        coll = db[coll_n]
        doc = coll.find_one({"_id": ObjectId(mongo_id)})
        return doc
