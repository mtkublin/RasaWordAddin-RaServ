from rasa_nlu.model import Trainer
from rasa_nlu.model import Interpreter
from rasa_nlu.training_data.formats import RasaReader
from rasa_nlu import config
from mongo_utils import MongoHandler
import warnings
import os
import shutil
import threading

warnings.filterwarnings(module='h5py*', action='ignore', category=FutureWarning)


class statuses():
    NEW = "new"
    STARTED = "started"
    COMPLETED = "completed"
    DONE = "done"
    ERROR = "error"


uri = "mongodb://mtkublin:dVyBCQYJkUpFNbph85YLPg54SNa3m4gFnXzq0l8T4GvSVx8QlyZstb1urTKVaOtxoUzT5dLfYQcuQNL6ytNEzA==@mtkublin.documents.azure.com:10255/?ssl=true&replicaSet=globaldb"
db_name = 'train_data_test'
mongo = MongoHandler(uri, db_name)


class TrainThread(threading.Thread):
    def __init__(self, lock, interpreter_dict, training_data, project_name, model_name, persistor, TRAIN_DATA):
        self.lock = lock
        self.interpreter_dict = interpreter_dict
        self.training_data = training_data
        self.project_name = project_name
        self.model_name = model_name
        self.persistor = persistor
        self.TRAIN_DATA = TRAIN_DATA

        threading.Thread.__init__(self)

    def run(self):
        self.lock.acquire()
        initiate_training(self.training_data, self.project_name, self.model_name, self.interpreter_dict, self.persistor, self.TRAIN_DATA)
        self.lock.release()


class UpdateInterpreterThread(threading.Thread):
    def __init__(self, lock, interpreter_dict, model_name, project_name, force, persistor, model_path=None):
        self.lock = lock
        self.interpreter_dict = interpreter_dict
        self.model_name = model_name
        self.project_name = project_name
        self.force = force
        self.persistor = persistor
        self.model_path = model_path

        threading.Thread.__init__(self)

    def run(self):
        self.lock.acquire()
        load_interpreter(self.interpreter_dict, self.model_name, self.project_name, self.force, self.persistor, self.model_path)
        self.lock.release()


# LOAD ----------------------------------------------------------------------------------------------------------------


def load_interpreter(interpreter_dict, model_name, project_name, force, persistor, model_path):
    print(model_path["DATA"])
    if project_name not in interpreter_dict["interpreters"].keys() or model_name not in interpreter_dict["interpreters"][project_name].keys() or force == "True":

        if model_path["DATA"] == "":
            persistor.retrieve(model_name=model_name, project=project_name, target_path='.\\temp_test_model')

            rm_path = '.\\' + project_name + '___' + model_name + '.tar.gz'
            os.remove(rm_path)
            new_model_path = ".\\temp_test_model"
            print("AZURE")

        else:
            new_model_path = model_path["DATA"]
            print("LOCAL")
            print(new_model_path)

        print("Loading interpreter")
        warnings.filterwarnings(module='rasa_nlu*', action='ignore', category=UserWarning)
        interpreter = Interpreter.load(new_model_path)
        warnings.filterwarnings(module='sklearn*', action='ignore', category=DeprecationWarning)
        print("Loaded")

        if model_path["DATA"] == "":
            shutil.rmtree('.\\temp_test_model')

        if project_name not in interpreter_dict["interpreters"].keys():
            interpreter_dict["interpreters"][project_name] = {model_name: interpreter}
        else:
            interpreter_dict["interpreters"][project_name][model_name] = interpreter

    interpreter_dict["current_project"] = project_name
    interpreter_dict["current_model"] = model_name


# TRAIN ----------------------------------------------------------------------------------------------------------------


def initiate_training(training_data, project_name, model_name, interpreter_dict, persistor, TRAIN_DATA):
    req_id = training_data["req_id"]

    if "model_path" in training_data.keys():
        model_path = training_data["model_path"]
        data_id = training_data["data_id"]
        f = open("%s\\TRAIN_DATA\\%s\\%s_%s.json" % (model_path, project_name, data_id, model_name), "r")
        train_doc = eval(f.read())
        f.close()
        TRAIN_DATA[req_id]["status"] = statuses.STARTED
        train_model(interpreter_dict, persistor, train_doc, project_name, model_name, model_path)

    else:
        mongo_id = training_data["mongo_id"]
        doc = mongo.mongo_get(mongo_id)
        train_doc = {"rasa_nlu_data": doc["rasa_nlu_data"]}
        TRAIN_DATA[req_id]["status"] = statuses.STARTED
        train_model(interpreter_dict, persistor, train_doc, project_name, model_name)

    TRAIN_DATA[req_id]["status"] = statuses.COMPLETED


def train_model(interpreter_dict, persistor, json_data, proj_name, mod_name, model_path = None):
    reader = RasaReader()
    training_data = reader.read_from_json(json_data)
    trainer = Trainer(config.load(".\\config.yml"))
    interpreter = trainer.train(training_data)
    if model_path is None:
        os.mkdir('.\\temp_train_model')
        trainer.persist(path='.\\temp_train_model', persistor=persistor, project_name= proj_name, fixed_model_name= mod_name)
        shutil.rmtree('.\\temp_train_model')
    else:
        trainer.persist(path=model_path + "\\MODELS", project_name= proj_name, fixed_model_name= mod_name)

    if proj_name not in interpreter_dict["interpreters"].keys():
        interpreter_dict["interpreters"][proj_name] = {mod_name: interpreter}
    else:
        interpreter_dict["interpreters"][proj_name][mod_name] = interpreter

    interpreter_dict["current_project"] = proj_name
    interpreter_dict["current_model"] = mod_name


# TEST ----------------------------------------------------------------------------------------------------------------


def test_with_model(interpreter_dict, test_data, TEST_DATA, TEST_DATA_RES):
    req_id = test_data["req_id"]
    doc = test_data["test_data"]
    TEST_DATA[req_id] = {"req_id": req_id, "SENTS": doc["SENTS"]}

    print("Proceeding to test:", req_id)

    cur_proj = interpreter_dict["current_project"]
    cur_mod = interpreter_dict["current_model"]
    interpreter = interpreter_dict["interpreters"][cur_proj][cur_mod]

    sents_list_to_test = TEST_DATA[req_id]["SENTS"]

    res_list = []
    for text_to_test in sents_list_to_test:
        result = interpreter.parse(text_to_test)
        res_list += [result]

    TEST_DATA_RES[req_id] = {"req_id": req_id, "result": res_list}

    print("Test ", req_id, ": FINISHED")
