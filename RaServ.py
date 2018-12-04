from rasa_nlu.model import Trainer
from rasa_nlu.model import Interpreter
from rasa_nlu.training_data.formats import RasaReader
from rasa_nlu import config
from mongo_utils import mongo_get
import warnings
import os
import shutil
import threading


class statuses():
    NEW = "new"
    STARTED = "started"
    COMPLETED = "completed"
    DONE = "done"
    ERROR = "error"


warnings.filterwarnings(module='h5py*', action='ignore', category=FutureWarning)


class TrainThread(threading.Thread):
    def __init__(self, lock, interpreter_dict, training_data, project_name, model_name, persistor, TRAIN_DATA):
        self.lock = lock
        self.interpreter_dict = interpreter_dict
        self.training_data = training_data
        self.project_name = project_name
        self.model_name = model_name
        self.persistor = persistor
        self.TRAIN_DATA = TRAIN_DATA
        # self.TRAINING_DOCS = TRAINING_DOCS

        threading.Thread.__init__(self)

    def run(self):
        self.lock.acquire()

        req_id = self.training_data["req_id"]

        if "model_path" in self.training_data.keys():
            model_path = self.training_data["model_path"]
            data_id = self.training_data["data_id"]
            f = open(model_path + "\\TRAIN_DATA\\" + data_id + ".json", "r")
            train_doc = eval(f.read())
            f.close()
            train_model(self.interpreter_dict, self.persistor, train_doc, self.project_name, self.model_name, model_path)

        else:
            mongo_id = self.training_data["mongo_id"]
            doc = mongo_get(mongo_id)
            # self.TRAINING_DOCS[mongo_id] = doc["rasa_nlu_data"]
            # train_doc = {"rasa_nlu_data": self.TRAINING_DOCS[mongo_id]}
            train_doc = {"rasa_nlu_data": doc["rasa_nlu_data"]}
            train_model(self.interpreter_dict, self.persistor, train_doc, self.project_name, self.model_name)

        # r = requests.put(url="http://127.0.0.1:6000/api/traindata/" + str(req_id))
        # print(r)
        self.TRAIN_DATA[req_id]["status"] = statuses.COMPLETED
        self.lock.release()

# class TestThread(threading.Thread):
#     def __init__(self, lock, interpreter_dict, test_data, TEST_DOCS, TEST_DATA_RES):
#         threading.Thread.__init__(self)
#         self.lock = lock
#         self.test_data = test_data
#         self.TEST_DOCS = TEST_DOCS
#         self.interpreter_dict = interpreter_dict
#         self.TEST_DATA_RES = TEST_DATA_RES
#
#     def run(self):
#         self.lock.acquire()
#         test_with_model(self.interpreter_dict, self.test_data, self.TEST_DOCS, self.TEST_DATA_RES)
#         self.lock.release()


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


def test_with_model(interpreter_dict, test_data, TEST_DATA, TEST_DATA_RES):
    req_id = test_data["req_id"]
    doc = test_data["test_data"]
    TEST_DATA[req_id] = {"req_id": req_id,
                              "SENTS": doc["SENTS"]}

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


# def get_projects_list(persistor):
#     projects_list = persistor.list_projects()
#     return projects_list
#
#
# def get_models_list(persistor, project):
#     models_list = persistor.list_models(project)
#     return models_list
