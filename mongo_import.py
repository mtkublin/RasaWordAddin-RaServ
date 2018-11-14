from pymongo import MongoClient

uri = "mongodb://mtkublin:dVyBCQYJkUpFNbph85YLPg54SNa3m4gFnXzq0l8T4GvSVx8QlyZstb1urTKVaOtxoUzT5dLfYQcuQNL6ytNEzA==@mtkublin.documents.azure.com:10255/?ssl=true&replicaSet=globaldb"
db_name = 'train_data_test'


def mongoimport_train(json_obj, uri = uri, db_name = db_name, coll_name = 'train_data'):

    print(type(json_obj))
    client = MongoClient(uri)
    db = client[db_name]
    coll = db[coll_name]

    coll.insert_one(json_obj)
    # return coll.estimated_document_count()


def mongoimport_test(json_obj, uri = uri, db_name = db_name, coll_name = 'test_data'):

    client = MongoClient(uri)
    db = client[db_name]
    coll = db[coll_name]

    coll.insert_one(json_obj)
    # return coll.estimated_document_count()
