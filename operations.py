from flask import abort
from rasa_nlu.persistor import AzurePersistor
from mongo_utils import mongo_import
from RaServ import UpdateInterpreterThread, TrainThread, TestThread, ThreadKiller
from threading import Lock, Event
import queue
import warnings
import requests
import uuid
import json

lock = Lock()
waiting_event = Event()

warnings.filterwarnings(module='h5py*', action='ignore', category=FutureWarning)


persistor = AzurePersistor(azure_container= 'rasa-models-test-container', azure_account_name= 'csb6965281488a3x4dd7xbcd',
                           azure_account_key= 'ZT4DVNgFfQrbglJXzUX2HuPi6KYysL3b2zxdNlL11umXg811fptnTcubKQ83itTLDAmSdmfqgpiJWylbfumTDQ==')

interpreter_dict = {"current_project": "", "current_model": "", "interpreters": {}}

TRAINING_DOCS = {}
TEST_DOCS = {}


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
threads = {}

# PROJECTS AND MODELS --------------------------------------------------------------------------------------------------


# def get_all_projects():
#     r = requests.get(url="http://127.0.0.1:8000/api/projects")
#     proj_list = r.json()
#     return proj_list
#
#
# def get_all_models(project):
#     r = requests.get(url="http://127.0.0.1:8000/api/models/" + str(project))
#     models_list = r.json()
#     return models_list
#
#
# def update_interpreter_local(project, model, force, model_path):
#     uri = "http://127.0.0.1:8000/api/interpreter/local/" + str(project) + '/' + str(model) + '/' + str(force)
#     r = requests.post(url=uri, json=model_path)


def get_all_projects():
    projects_list = persistor.list_projects()
    return projects_list


def get_all_models(project):
    models_list = persistor.list_models(project)
    return models_list


def update_interpreter(project, model, force, model_path):
    print(interpreter_dict)
    thread_id = str(uuid.uuid1())
    threads[thread_id] = UpdateInterpreterThread(lock, waiting_event, interpreter_dict, model, project, force, persistor, model_path)
    threads[thread_id].start()
    ThreadKiller(waiting_event, threads, thread_id).start()
    return "Succesfuly updated interpreter", 201


# TRAIN ----------------------------------------------------------------------------------------------------------------


def train_create(t_data_instance, project, model):
    req_id_nr = 0
    for key in TRAIN_DATA:
        req_id_nr += 1
    req_id = "train_" + str(req_id_nr)
    t_data_all = t_data_instance.get("DATA", None)
    t_data = {"rasa_nlu_data": t_data_all["rasa_nlu_data"]}

    if req_id not in TRAIN_DATA and req_id is not None:

        if t_data_all["ModelPath"] is not None:
            data_id = str(uuid.uuid1())
            data_path = t_data_all["ModelPath"]
            f = open(data_path + "\\TRAIN_DATA\\" + data_id + ".json", "w")
            json.dump(t_data, f)
            f.close()

            TRAIN_DATA[req_id] = {
                "req_id": req_id,
                "model_path": data_path,
                "data_id": data_id,
                "status": statuses.NEW,
            }

        else:
            mongo_id = mongo_import(json_obj=t_data)
            TRAIN_DATA[req_id] = {
                "req_id": req_id,
                "mongo_id": mongo_id,
                "status": statuses.NEW,
            }

        task_queue.put(req_id)

        if started["isStarted"] is None:
            started["isStarted"] = task_queue.get()
            print("JUST STARTED: " + str(started["isStarted"]))
            data_to_send = TRAIN_DATA[started["isStarted"]]
            r = requests.post(url="http://127.0.0.1:8000/api/train/" + str(project) + "/" + str(model),
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
