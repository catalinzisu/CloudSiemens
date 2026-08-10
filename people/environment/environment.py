from flask import request
from flask_restful import Resource, Api

app = Flask("environment")
api = Api(app)

class Environment:
    def __init__(self):
        pass

    def get_status(self, apartment_nr, building_id):
        return "yes"

api.add_resource(Environment, "/status")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)