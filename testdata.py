from flask import abort
from mongo_import import mongo_import, mongo_get
import requests
from traindata import train_queue


class statuses():
    NEW = "new"
    STARTED = "started"
    COMPLETED = "completed"
    DONE = "done"
    ERROR = "error"


TEST_DATA = {}
TEST_DATA_RES = {}
# test_queue = queue.Queue()
test_started = {"isStarted": None}


def test_create(t_data_instance):
    req_id = 0
    for key in TEST_DATA:
        req_id += 1
    req_id = "test_" + str(req_id)
    t_data = t_data_instance.get("DATA", None)
    if req_id not in TEST_DATA and req_id is not None:
        mongo_id = mongo_import(json_obj=t_data, coll_name="unprocessed_test_data")
        TEST_DATA[req_id] = {
            "req_id": req_id,
            "mongo_id": mongo_id,
            "status": statuses.NEW
        }
        train_queue.put(req_id)

        if test_started["isStarted"] is None:
            test_started["isStarted"] = train_queue.get()
            print("JUST STARTED: " + str(test_started["isStarted"]))
            data_to_send = TEST_DATA[test_started["isStarted"]]
            r = requests.post(url="http://127.0.0.1:8000/api/test",
                              json={"DATA": data_to_send})
            print("POST: " + r.text)
        else:
            print("STARTED EARLIER: " + str(test_started["isStarted"]))
            print("STARTED: " + str(test_started))
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
    mongo_id = t_data_res["DATA"]["mongo_id"]

    test_started["isStarted"] = None
    TEST_DATA[req_id]["status"] = statuses.COMPLETED
    print("STARTED: " + str(test_started))

    res_doc = mongo_get(mongo_id, coll_n="test_results")
    TEST_DATA_RES[req_id] = res_doc["RESULT"]

    return TEST_DATA_RES[req_id]


def test_read_all():
    return [TEST_DATA[key] for key in sorted(TEST_DATA.keys())]


def test_read_all_res():
    return [TEST_DATA_RES[key] for key in sorted(TEST_DATA_RES.keys())]


def test_read_one_res(req_id):
    return TEST_DATA_RES[req_id]
