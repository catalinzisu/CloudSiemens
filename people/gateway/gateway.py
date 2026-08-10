import os

from flask import request, Flask
from flask_restful import Resource, Api
import json

app = Flask("api/gateway")
api = Api(app)

people_host = os.environ.get("PEOPLE_HOST")
people_port = os.environ.get("PEOPLE_PORT")
environment_host = os.environ.get("ENVIRONMENT_HOST")
environment_port = os.environ.get("ENVIRONMENT_PORT")

class GatewayResource(Resource):
    def __init__(self):

    def get_dashboard(self):
        id = request.args.get("id")
        if not id:
            return {"error": "Missing id parameter"}, 400
        try:
            user = requests.get(f"http://{people_host}:{people_port}/people?id={id}").json()
            environment = requests.get(f"http://{environment_host}:{environment_port}/environment/status?apartment={user.apartment}&building_id={user.building_id}").json()
        except Exception as e:
            return {"error": str(e)}, 500
        return json.dumps({
            "name": user.first_name + " " + user.last_name,
            "apartment": user.apartment,
            "environment": environment
        })

api.add_resource(GatewayResource, "/dashboard")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)