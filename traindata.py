from datetime import datetime
from flask import make_response, abort
from mongo_import import mongoimport_train

def get_timestamp():
    return datetime.now().strftime(("%Y-%m-%d %H:%M:%S"))

TRAIN_DATA = {
    "0": {
        "dataid": "0",
        "DATA": {},
        "timestamp": get_timestamp(),
    },
}

def read_all():
    return [TRAIN_DATA[key] for key in sorted(TRAIN_DATA.keys())]

def read_one(dataid):
    if dataid in TRAIN_DATA:
        t_data = TRAIN_DATA.get(dataid)
    else:
        abort(
            404, "dataid {dataid} not found".format(dataid=dataid)
        )
    return t_data

def create(t_data_instance):
    dataid = 0
    for key in TRAIN_DATA:
        dataid += 1
    dataid = str(dataid)
    t_data = t_data_instance.get("DATA", None)
    if dataid not in TRAIN_DATA and dataid is not None:
        TRAIN_DATA[dataid] = {
            "dataid": dataid,
            "DATA": t_data,
            "timestamp": get_timestamp(),
        }
        mongoimport_train(json_obj=t_data)
        return TRAIN_DATA[dataid], 201
    else:
        abort(
            406,
            "dataid overlapping existing one".format(dataid=dataid),
        )

def delete(dataid):
    if dataid in TRAIN_DATA:
        del TRAIN_DATA[dataid]
        return make_response(
            "{dataid} successfully deleted".format(dataid=dataid), 200
        )

    else:
        abort(
            404, "dataid {dataid} not found".format(dataid=dataid)
        )