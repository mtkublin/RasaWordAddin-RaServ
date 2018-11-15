from datetime import datetime
from flask import make_response, abort


def get_timestamp():
    return datetime.now().strftime(("%Y-%m-%d %H:%M:%S"))


TEST_DATA = {}


def read_all():
    return [TEST_DATA[key] for key in sorted(TEST_DATA.keys())]


def read_one(req_id):
    if req_id in TEST_DATA:
        t_data = TEST_DATA.get(req_id)
    else:
        abort(
            404, "req_id {req_id} not found".format(req_id=req_id)
        )
    return t_data


def read_latest():
    req_id = -1
    for key in TEST_DATA:
        req_id += 1
    req_id = str(req_id)
    if req_id in TEST_DATA:
        t_data = TEST_DATA.get(req_id)
    else:
        abort(
            404, "req_id {req_id} not found".format(req_id=req_id)
        )
    return t_data


def delete(req_id):
    if req_id in TEST_DATA:
        del TEST_DATA[req_id]
        return make_response(
            "{req_id} successfully deleted".format(req_id=req_id), 200
        )
    else:
        abort(
            404, "req_id {req_id} not found".format(req_id=req_id)
        )
