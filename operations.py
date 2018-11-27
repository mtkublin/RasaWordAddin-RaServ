from flask import abort
from mongo_utils import mongo_import, mongo_get
import queue
import requests


class statuses():
    NEW = "new"
    STARTED = "started"
    COMPLETED = "completed"
    DONE = "done"
    ERROR = "error"


TRAIN_DATA = {}
TEST_DATA = {}
TEST_DATA_RES = {}
task_queue = queue.Queue()
started = {"isStarted": None}


def train_create(t_data_instance):
    req_id_nr = 0
    for key in TRAIN_DATA:
        req_id_nr += 1
    req_id = "train_" + str(req_id_nr)
    t_data = t_data_instance.get("DATA", None)
    if req_id not in TRAIN_DATA and req_id is not None:
        mongo_id = mongo_import(json_obj=t_data)
        TRAIN_DATA[req_id] = {
            "req_id": req_id,
            "mongo_id": mongo_id,
            "status": statuses.NEW
        }
        task_queue.put(req_id)

        if started["isStarted"] is None:
            started["isStarted"] = task_queue.get()
            print("JUST STARTED: " + str(started["isStarted"]))
            data_to_send = TRAIN_DATA[started["isStarted"]]
            r = requests.post(url="http://127.0.0.1:8000/api/train",
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


def train_completed(req_id):
    started["isStarted"] = None
    print("STARTED: " + str(started))
    TRAIN_DATA[req_id]["status"] = statuses.COMPLETED
    return TRAIN_DATA[req_id]


def train_read_all():
    return [TRAIN_DATA[key] for key in sorted(TRAIN_DATA.keys())]


# TEST ----------------------------------------------------------------------------------------------------------------


def test_create(t_data_instance):
    req_id_nr = 0
    for key in TEST_DATA:
        req_id_nr += 1
    req_id = "test_" + str(req_id_nr)
    t_data = t_data_instance.get("DATA", None)
    if req_id not in TEST_DATA and req_id is not None:
        # mongo_id = mongo_import(json_obj=t_data, coll_name="unprocessed_test_data")

        TEST_DATA[req_id] = {
            "req_id": req_id,
            "test_data": t_data,
            # "mongo_id": mongo_id,
            "status": statuses.NEW
        }
        task_queue.put(req_id)

        if started["isStarted"] is None:
            started["isStarted"] = task_queue.get()
            print("JUST STARTED: " + str(started["isStarted"]))
            data_to_send = TEST_DATA[started["isStarted"]]
            r = requests.post(url="http://127.0.0.1:8000/api/test",
                              json={"DATA": data_to_send})
            print("POST: " + r.text)
        else:
            print("STARTED EARLIER: " + str(started["isStarted"]))
            print("STARTED: " + str(started))
        return TEST_DATA[req_id], 201
    else:
        abort(
            406,
            "req_id overlapping existing one".format(req_id=req_id),
        )


def test_start(req_id):
    TEST_DATA[req_id]["status"] = statuses.STARTED
    print("STARTED: " + str(TEST_DATA[req_id]["status"]))
    return TEST_DATA[req_id]


def test_completed(req_id, t_data_res):
    # mongo_id = t_data_res["DATA"]["mongo_id"]
    # res_doc = mongo_get(mongo_id, coll_n="test_results")

    res_doc = t_data_res["DATA"]["result"]

    started["isStarted"] = None
    TEST_DATA[req_id]["status"] = statuses.COMPLETED
    print("STARTED: " + str(started))

    TEST_DATA_RES[req_id] = res_doc

    return TEST_DATA_RES[req_id]


def test_read_all():
    return [TEST_DATA[key] for key in sorted(TEST_DATA.keys())]


def test_read_all_res():
    return [TEST_DATA_RES[key] for key in sorted(TEST_DATA_RES.keys())]


def test_read_one_res(req_id):
    return TEST_DATA_RES[req_id]
