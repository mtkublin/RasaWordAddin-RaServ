from rasa_nlu.model import Trainer
from rasa_nlu.model import Interpreter
from rasa_nlu.training_data.formats import RasaReader
from rasa_nlu import config
from mongo_utils import mongo_get
import warnings
import os
import shutil
import threading
import time
import requests

warnings.filterwarnings(module='h5py*', action='ignore', category=FutureWarning)


class TrainThread(threading.Thread):
    def __init__(self, train_data_id, project_name, model_name, persistor, TRAINING_DOCS):
        threading.Thread.__init__(self)
        self.train_data_id = train_data_id
        self.project_name = project_name
        self.model_name = model_name
        self.persistor = persistor
        self.TRAINING_DOCS = TRAINING_DOCS

    def run(self):
        req_id = self.train_data_id["DATA"]["req_id"]

        if "model_path" in self.train_data_id["DATA"].keys():
            model_path = self.train_data_id["DATA"]["model_path"]
            data_id = self.train_data_id["DATA"]["data_id"]
            f = open(model_path + "\\TRAIN_DATA\\" + data_id + ".json", "r")
            train_doc = eval(f.read())
            f.close()
            train_model(self.persistor, train_doc, self.project_name, self.model_name, model_path)

        else:
            mongo_id = self.train_data_id["DATA"]["mongo_id"]
            doc = mongo_get(mongo_id)
            self.TRAINING_DOCS[mongo_id] = doc["rasa_nlu_data"]
            train_doc = {"rasa_nlu_data": self.TRAINING_DOCS[mongo_id]}
            train_model(self.persistor, train_doc, self.project_name, self.model_name)

        r = requests.put(url="http://127.0.0.1:6000/api/traindata/" + str(req_id))
        print(r)


class TestThread(threading.Thread):
    def __init__(self, test_data, TEST_DOCS, interpreter_dict):
        threading.Thread.__init__(self)
        self.test_data = test_data
        self.TEST_DOCS = TEST_DOCS
        self.interpreter_dict = interpreter_dict

    def run(self):
        req_id = self.test_data["DATA"]["req_id"]
        doc = self.test_data["DATA"]["test_data"]
        self.TEST_DOCS[req_id] = {"req_id": req_id,
                             "SENTS": doc["SENTS"]}
        r = requests.put(url="http://127.0.0.1:6000/api/testdata/" + str(req_id))
        print(r)

        print("Proceeding to test")
        result_data = test_with_model(self.interpreter_dict, self.TEST_DOCS[req_id]["SENTS"])

        data_to_send = {"req_id": req_id,
                        "result": result_data}
        r2 = requests.post(url="http://127.0.0.1:6000/api/testdata/" + str(req_id),
                           json={"DATA": data_to_send})
        print(r2)


class UpdateInterpreterThread(threading.Thread):
    def __init__(self, lock, event, interpreter_dict, model_name, project_name, force, persistor, model_path=None):
        self.lock = lock
        self.event = event
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
        self.event.set()
        self.lock.release()


class ThreadKiller(threading.Thread):
    def __init__(self, event, threads, thread_id):
        self.event = event
        self.threads = threads
        self.thread_id = thread_id

        threading.Thread.__init__(self)

    def run(self):
        self.event.wait()
        self.threads[self.thread_id].join()
        print("Thread %s terminated" % (self.thread_id))
        self.event.clear()


# RASA ----------------------------------------------------------------------------------------------------------------


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
        warnings.filterwarnings(module='sklearn*', action='ignore', category=DeprecationWarning)
        warnings.filterwarnings(module='rasa_nlu*', action='ignore', category=UserWarning)
        interpreter = Interpreter.load(new_model_path)
        warnings.filterwarnings(module='sklearn*', action='ignore', category=DeprecationWarning)
        warnings.filterwarnings(module='rasa_nlu*', action='ignore', category=UserWarning)
        print("Loaded")

        if model_path["DATA"] == "":
            shutil.rmtree('.\\temp_test_model')

        if project_name not in interpreter_dict["interpreters"].keys():
            interpreter_dict["interpreters"][project_name] = {model_name: interpreter}
        else:
            interpreter_dict["interpreters"][project_name][model_name] = interpreter

        interpreter_dict["current_project"] = project_name
        interpreter_dict["current_model"] = model_name

    interpreter_dict["current_project"] = project_name
    interpreter_dict["current_model"] = model_name
    print(interpreter_dict)


def train_model(persistor, json_data, proj_name, mod_name, model_path = None):
    reader = RasaReader()
    training_data = reader.read_from_json(json_data)
    trainer = Trainer(config.load(".\\config.yml"))
    trainer.train(training_data)
    if model_path is None:
        os.mkdir('.\\temp_train_model')
        trainer.persist(path='.\\temp_train_model', persistor=persistor, project_name= proj_name, fixed_model_name= mod_name)
        shutil.rmtree('.\\temp_train_model')
    else:
        trainer.persist(path=model_path + "\\MODELS", project_name= proj_name, fixed_model_name= mod_name)


def test_with_model(interpreter_dict, sents_list_to_test):
    cur_proj = interpreter_dict["current_project"]
    cur_mod = interpreter_dict["current_model"]
    interpreter = interpreter_dict["interpreters"][cur_proj][cur_mod]

    res_list = []
    for text_to_test in sents_list_to_test:
        result = interpreter.parse(text_to_test)
        res_list += [result]

    return res_list


def get_projects_list(persistor):
    projects_list = persistor.list_projects()
    return projects_list


def get_models_list(persistor, project):
    models_list = persistor.list_models(project)
    return models_list
