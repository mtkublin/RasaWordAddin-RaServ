from datetime import datetime
from flask import abort
from mongo_import import mongo_import
import queue
import requests

def get_timestamp():
    return datetime.now().strftime(("%Y-%m-%d %H:%M:%S"))


class statuses():
    NEW = "new"
    STARTED = "started"
    COMPLETED = "completed"
    DONE = "done"
    ERROR = "error"


TRAIN_DATA = {}
train_queue = queue.Queue()
started = {"isStarted": None}


def create(t_data_instance):
    req_id = 0
    for key in TRAIN_DATA:
        req_id += 1
    req_id = str(req_id)
    t_data = t_data_instance.get("DATA", None)
    if req_id not in TRAIN_DATA and req_id is not None:
        mongo_id = mongo_import(json_obj=t_data)
        TRAIN_DATA[req_id] = {
            "req_id": req_id,
            "mongo_id": mongo_id,
            "status": statuses.NEW
        }
        train_queue.put(req_id)

        if started["isStarted"] is None:
            started["isStarted"] = train_queue.get()
            print("JUST STARTED: " + str(started["isStarted"]))
            data_to_send = TRAIN_DATA[started["isStarted"]]
            r = requests.post(url="https://raserv.azurewebsites.net/api/train",
                              json={"DATA": data_to_send})
            print("POST: " + r.text)
        else:
            print("STARTED EARLIER: " + str(started["isStarted"]))
            print("STARTED: " + str(started))
        return TRAIN_DATA[req_id], 201
    else:
        abort(
            406,
            "req_id overlapping existing one".format(req_id=req_id),
        )


def completed(req_id):
    started["isStarted"] = None
    print("STARTED: " + str(started))
    TRAIN_DATA[req_id]["status"] = statuses.COMPLETED
    return TRAIN_DATA[req_id]


def read_all():
    return [TRAIN_DATA[key] for key in sorted(TRAIN_DATA.keys())]


# class CreateTrainData():
#     def __init__(self):
#         self.TRAIN_DATA = {}
#         self.train_queue = queue.Queue()
#         self.started = None
#
#     def create(self, t_data_instance):
#         req_id = 0
#         for key in self.TRAIN_DATA:
#             req_id += 1
#         req_id = str(req_id)
#         t_data = t_data_instance.get("DATA", None)
#         if req_id not in self.TRAIN_DATA and req_id is not None:
#             mongo_id = mongo_import(json_obj=t_data)
#             self.TRAIN_DATA[req_id] = {
#                 "req_id": req_id,
#                 "mongo_id": mongo_id,
#                 "status": statuses.NEW
#             }
#             self.train_queue.put(req_id)
#             if self.started == None:
#                 started = self.train_queue.get()
#                 print("JUST STARTED: " + str(started))
#                 data_to_send = self.TRAIN_DATA[started]
#                 r = requests.post(url="http://127.0.0.1:8000/api/traindata",
#                                   json={"DATA": data_to_send})
#                 print(r)
#             else:
#                 print("STARTED EARLIER: " + str(self.started))
#             return self.TRAIN_DATA[req_id], 201
#         else:
#             abort(
#                 406,
#                 "req_id overlapping existing one".format(req_id=req_id),
#             )
#
#     def completed(self, req_id):
#         self.started = None
#         self.TRAIN_DATA[req_id]["status"] = statuses.COMPLETED
#         return self.TRAIN_DATA[req_id]
#
#
#     def read_all(self):
#         return [self.TRAIN_DATA[key] for key in sorted(self.TRAIN_DATA.keys())]
