import connexion
import openapi_spec_validator
import templates
import venv
import mongo_utils, operations, RaServ

app = connexion.App(__name__, specification_dir="./")

app.add_api(".\\apiconfig.yml")


@app.route("/")
def home():
    return



if __name__ == "__main__":
    app.run(host='127.0.0.1', port=6000, debug=True)
