from rasa_nlu.persistor import AzurePersistor
from mongo_utils import MongoHandler
from RaServ import UpdateInterpreterThread, TrainThread, test_with_model
from threading import Lock, Event
import queue
import warnings
import uuid
import json
import os

warnings.filterwarnings(module='h5py*', action='ignore', category=FutureWarning)

lock = Lock()
waiting_event = Event()
persistor = AzurePersistor(azure_container= 'rasa-models-test-container', azure_account_name= 'csb6965281488a3x4dd7xbcd',
                           azure_account_key= 'ZT4DVNgFfQrbglJXzUX2HuPi6KYysL3b2zxdNlL11umXg811fptnTcubKQ83itTLDAmSdmfqgpiJWylbfumTDQ==')
uri = "mongodb://mtkublin:dVyBCQYJkUpFNbph85YLPg54SNa3m4gFnXzq0l8T4GvSVx8QlyZstb1urTKVaOtxoUzT5dLfYQcuQNL6ytNEzA==@mtkublin.documents.azure.com:10255/?ssl=true&replicaSet=globaldb"
db_name = 'train_data_test'
mongo = MongoHandler(uri, db_name)
interpreter_dict = {"current_project": "", "current_model": "", "interpreters": {}}
TRAIN_DATA = {}
TEST_DATA = {}
TEST_DATA_RES = {}
task_queue = queue.Queue()
started = {"isStarted": None}
threads = {}


class statuses():
    NEW = "new"
    STARTED = "started"
    COMPLETED = "completed"
    DONE = "done"
    ERROR = "error"


# PROJECTS AND MODELS --------------------------------------------------------------------------------------------------


def get_all_projects():
    projects_list = persistor.list_projects()
    return projects_list


def get_all_models(project):
    models_list = persistor.list_models(project)
    return models_list


def update_interpreter(project, model, force, model_path):
    thread_id = str(uuid.uuid1())
    threads[thread_id] = UpdateInterpreterThread(lock, interpreter_dict, model, project, force, persistor, model_path)
    threads[thread_id].start()
    return "Interpreter started updating", 201


def interpreter_is_loaded(project, model):
    print(interpreter_dict)
    if project in interpreter_dict["interpreters"].keys() and model in interpreter_dict["interpreters"][project].keys() \
            and interpreter_dict["current_project"] == project and interpreter_dict["current_model"] == model:
        response = "True"
    else:
        response = "False"
    return response


# TRAIN ----------------------------------------------------------------------------------------------------------------


def train_create(t_data_instance, project, model):
    req_id = "train_" + str(uuid.uuid1())
    t_data_all = t_data_instance.get("DATA", None)
    t_data = {"rasa_nlu_data": t_data_all["rasa_nlu_data"]}

    if t_data_all["ModelPath"] is not None:
        data_id = str(uuid.uuid1())
        data_path = "%s\\TRAIN_DATA\\%s" % (t_data_all["ModelPath"], project)
        if not os.path.exists(data_path):
            os.mkdir(data_path)
        f = open("%s\\%s_%s.json" % (data_path, data_id, model), "w")
        json.dump(t_data, f)
        f.close()

        TRAIN_DATA[req_id] = {
            "req_id": req_id,
            "model_path": t_data_all["ModelPath"],
            "data_id": data_id,
            "status": statuses.NEW,
        }

    else:
        mongo_id = mongo.mongo_import(json_obj=t_data)

        TRAIN_DATA[req_id] = {
            "req_id": req_id,
            "mongo_id": mongo_id,
            "status": statuses.NEW,
        }

    data_to_send = TRAIN_DATA[req_id]

    thread_id = str(uuid.uuid1())
    threads[thread_id] = TrainThread(lock, interpreter_dict, data_to_send, project, model, persistor, TRAIN_DATA)
    threads[thread_id].start()

    return req_id


def train_read_all():
    return [TRAIN_DATA[key] for key in sorted(TRAIN_DATA.keys())]


def train_is_finished(req_id):
    if req_id in TRAIN_DATA.keys():
        if TRAIN_DATA[req_id]["status"] == statuses.COMPLETED:
            TRAIN_DATA[req_id]["status"] = statuses.DONE
            print(req_id, statuses.DONE)
            return "True"
        else:
            return "False"
    else:
        return "ID not found"


# TEST ----------------------------------------------------------------------------------------------------------------


def test_create(t_data_instance):
    lock.acquire()
    req_id = "test_" + str(uuid.uuid1())
    t_data = t_data_instance.get("DATA", None)

    TEST_DATA[req_id] = {
        "req_id": req_id,
        "test_data": t_data,
        "status": statuses.NEW
    }

    data_to_send = TEST_DATA[req_id]

    print(interpreter_dict)

    test_with_model(interpreter_dict, data_to_send, TEST_DATA, TEST_DATA_RES)
    lock.release()
    return TEST_DATA_RES[req_id]["result"]


def test_read_all_res():
    return [TEST_DATA_RES[key] for key in sorted(TEST_DATA_RES.keys())]





