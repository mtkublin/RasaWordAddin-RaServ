from datetime import datetime
from flask import make_response, abort

def get_timestamp():
    return datetime.now().strftime(("%Y-%m-%d %H:%M:%S"))

TRAIN_DATA = {
    0: {
        "IDX": 0,
        "DATA": {},
        "timestamp": get_timestamp(),
    },
}

def read_all():
    return [TRAIN_DATA[key] for key in sorted(TRAIN_DATA.keys())]

def read_one(IDX):
    if IDX in TRAIN_DATA:
        t_data = TRAIN_DATA.get(IDX)
    else:
        abort(
            404, "IDX {IDX} not found".format(IDX=IDX)
        )
    return t_data

def create(t_data_instance):
    IDX = 0
    for key in TRAIN_DATA:
        IDX += 1
    t_data = t_data_instance.get()
    if IDX not in TRAIN_DATA and IDX is not None:
        TRAIN_DATA[IDX] = {
            "DATA": t_data,
            "timestamp": get_timestamp(),
        }
        return TRAIN_DATA[IDX], 201
    else:
        abort(
            406,
            "IDX overlapping existing one".format(IDX=IDX),
        )

def delete(IDX):
    if IDX in TRAIN_DATA:
        del TRAIN_DATA[IDX]
        return make_response(
            "{IDX} successfully deleted".format(IDX=IDX), 200
        )

    else:
        abort(
            404, "IDX {IDX} not found".format(IDX=IDX)
        )