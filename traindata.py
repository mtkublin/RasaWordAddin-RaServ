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
que = queue.Queue()
started = []

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
        que.put(req_id)
        if len(started) == 0:
            started.append(que.get())
            print("JUST STARTED: " + str(started[0]))
            data_to_send = TRAIN_DATA[started[0]]
            r = requests.post(url="http://127.0.0.1:8000/api/traindata",
                              json={"DATA": data_to_send})
        else:
            print("STARTED EARLIER: " + str(started[0]))
        return TRAIN_DATA[req_id], 201
    else:
        abort(
            406,
            "req_id overlapping existing one".format(req_id=req_id),
        )


def completed(req_id):
    started = []
    TRAIN_DATA[req_id]["status"] = statuses.COMPLETED
    return TRAIN_DATA[req_id]


def read_all():
    return [TRAIN_DATA[key] for key in sorted(TRAIN_DATA.keys())]
