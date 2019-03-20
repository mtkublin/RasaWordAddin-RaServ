from rasa_nlu.model import Trainer
from rasa_nlu.model import Interpreter
from rasa_nlu.training_data.formats import RasaReader
from rasa_nlu import config
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


class TrainThread(threading.Thread):
    def __init__(self, lock, interpreter_dict, training_data, project_name, model_name, persistor, TRAIN_DATA):
        self.__lock = lock
        self.__interpreter_dict = interpreter_dict
        self.__training_data = training_data
        self.__project_name = project_name
        self.__model_name = model_name
        self.__persistor = persistor
        self.__TRAIN_DATA = TRAIN_DATA

        threading.Thread.__init__(self)

    def __del__(self):
        print("Deleting object")

    def run(self):
        self.__lock.acquire()
        self.initiate_training(self.__training_data, self.__project_name, self.__model_name, self.__interpreter_dict, self.__persistor, self.__TRAIN_DATA)
        self.__lock.release()

    def initiate_training(self, training_data, project_name, model_name, interpreter_dict, persistor, TRAIN_DATA):
        req_id = training_data["req_id"]

        model_path = training_data["model_path"]
        data_id = training_data["data_id"]
        f = open("%s\\TRAIN_DATA\\%s\\%s_%s.json" % (model_path, project_name, data_id, model_name), "r")
        train_doc = eval(f.read())
        f.close()
        TRAIN_DATA[req_id]["status"] = statuses.STARTED
        self.train_model(self, interpreter_dict, persistor, train_doc, project_name, model_name, model_path)

        TRAIN_DATA[req_id]["status"] = statuses.COMPLETED

    def train_model(self, interpreter_dict, persistor, json_data, proj_name, mod_name, model_path=None):
        reader = RasaReader()
        training_data = reader.read_from_json(json_data)
        trainer = Trainer(config.load(".\\trainer_config.yml"))
        interpreter = trainer.train(training_data)
        if model_path is None:
            os.mkdir('.\\temp_train_model')
            trainer.persist(path='.\\temp_train_model', persistor=persistor, project_name=proj_name,
                            fixed_model_name=mod_name)
            shutil.rmtree('.\\temp_train_model')
        else:
            trainer.persist(path=model_path + "\\MODELS", project_name=proj_name, fixed_model_name=mod_name)

        if proj_name not in interpreter_dict["interpreters"].keys():
            interpreter_dict["interpreters"][proj_name] = {mod_name: interpreter}
        else:
            interpreter_dict["interpreters"][proj_name][mod_name] = interpreter

        interpreter_dict["current_project"] = proj_name
        interpreter_dict["current_model"] = mod_name


class UpdateInterpreterThread(threading.Thread):
    def __init__(self, lock, interpreter_dict, model_name, project_name, force, persistor, model_path=None):
        self.__lock = lock
        self.__interpreter_dict = interpreter_dict
        self.__model_name = model_name
        self.__project_name = project_name
        self.__force = force
        self.__persistor = persistor
        self.__model_path = model_path
        threading.Thread.__init__(self)

    def __del__(self):
        print("Deleting object")

    def run(self):
        self.__lock.acquire()
        self.load_interpreter(self.__interpreter_dict, self.__model_name, self.__project_name, self.__force, self.__persistor, self.__model_path)
        self.__lock.release()

    def load_interpreter(self, interpreter_dict, model_name, project_name, force, persistor, model_path):
        print(model_path["DATA"])
        if project_name not in interpreter_dict["interpreters"].keys() or model_name not in \
                interpreter_dict["interpreters"][project_name].keys() or force == "True":

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


class TesterClass():
    def __init__(self, this_test_data, this_TEST_DATA, this_TEST_DATA_RES, this_interpreter_dict):
        self.__test_data = this_test_data
        self.__TEST_DATA = this_TEST_DATA
        self.__TEST_DATA_RES = this_TEST_DATA_RES
        self.__interpreter_dict = this_interpreter_dict

    def __del__(self):
        print("Deleting object")

    def test_with_model(self):
        req_id = self.__test_data["req_id"]
        doc = self.__test_data["test_data"]
        self.__TEST_DATA[req_id] = {"req_id": req_id, "SENTS": doc["SENTS"]}

        print("Proceeding to test:", req_id)

        cur_proj = self.__interpreter_dict["current_project"]
        cur_mod = self.__interpreter_dict["current_model"]
        interpreter = self.__interpreter_dict["interpreters"][cur_proj][cur_mod]

        sents_list_to_test = self.__TEST_DATA[req_id]["SENTS"]

        res_list = []
        for text_to_test in sents_list_to_test:
            result = interpreter.parse(text_to_test)
            res_list += [result]

        self.__TEST_DATA_RES[req_id] = {"req_id": req_id, "result": res_list}

        print("Test ", req_id, ": FINISHED")

