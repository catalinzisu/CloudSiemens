import os
import requests
from flask import Flask, request
from flask_restful import Resource, Api

app = Flask("api/gateway")
api = Api(app)

people_host = os.environ.get("PEOPLE_HOST", "people")
people_port = os.environ.get("PEOPLE_PORT", "5000")
environment_host = os.environ.get("ENVIRONMENT_HOST", "environment")
environment_port = os.environ.get("ENVIRONMENT_PORT", "5001")

def _payload():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict() or {}

class ArriveHomeResource(Resource):
    def post(self):
        data = _payload()
        user_id = data.get("user_id")
        if not user_id:
            return {"error": "Missing user_id"}, 400
        
        # Forward the request to Environment Service to sync preferences
        env_url = f"http://{environment_host}:{environment_port}/environment/sync-preferences"
        try:
            response = requests.post(env_url, json={"user_id": user_id}, timeout=5)
            if response.status_code != 200:
                return {"error": "Environment service failed to sync", "details": response.json()}, response.status_code
            return response.json(), 200
        except Exception as e:
            return {"error": f"Failed to contact Environment service: {str(e)}"}, 500


class DashboardResource(Resource):
    def get(self, user_id):
        # 1. Get user profile
        people_url = f"http://{people_host}:{people_port}/people?id={user_id}"
        try:
            user_response = requests.get(people_url, timeout=5)
            if user_response.status_code != 200:
                return {"error": "Failed to fetch user profile"}, user_response.status_code
            user_data = user_response.json()
        except Exception as e:
            return {"error": f"Failed to contact People service: {str(e)}"}, 500
        
        if "error" in user_data:
            return {"error": user_data["error"]}, 404

        building_id = user_data.get("building_id")
        apartment_number = user_data.get("apartment_number")

        # 2. Get environment status
        env_url = f"http://{environment_host}:{environment_port}/environment/status?building_id={building_id}&apartment_number={apartment_number}"
        try:
            env_response = requests.get(env_url, timeout=5)
            environment_data = env_response.json() if env_response.status_code == 200 else []
        except:
            environment_data = []

        return {
            "name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip() if user_data.get('first_name') else user_data.get('email'),
            "apartment_number": apartment_number,
            "building_id": building_id,
            "environment": environment_data
        }, 200


class TenantMoveOutResource(Resource):
    def post(self):
        data = _payload()
        user_id = data.get("user_id")
        if not user_id:
            return {"error": "Missing user_id"}, 400

        # 1. Fetch user to get location before deleting
        people_url = f"http://{people_host}:{people_port}/people?id={user_id}"
        try:
            user_response = requests.get(people_url, timeout=5)
            if user_response.status_code != 200:
                return {"error": "User not found or People service error"}, 404
            user_data = user_response.json()
        except Exception as e:
            return {"error": f"Failed to contact People service: {str(e)}"}, 500

        if "error" in user_data:
            return {"error": user_data["error"]}, 404

        building_id = user_data.get("building_id")
        apartment_number = user_data.get("apartment_number")

        # 2. Delete User
        try:
            del_response = requests.delete(people_url, timeout=5)
            if del_response.status_code not in [200, 204]:
                return {"error": "Failed to delete user in People service"}, 500
        except Exception as e:
            return {"error": f"Failed to delete user: {str(e)}"}, 500

        # 3. Fetch environment devices
        env_status_url = f"http://{environment_host}:{environment_port}/environment/status?building_id={building_id}&apartment_number={apartment_number}"
        try:
            env_response = requests.get(env_status_url, timeout=5)
            devices = env_response.json() if env_response.status_code == 200 else []
        except:
            devices = []

        # 4. Switch devices to OFF (ECO mode)
        for device in devices:
            device_id = device.get("id")
            if device_id:
                try:
                    update_url = f"http://{environment_host}:{environment_port}/environment/device/{device_id}"
                    current_state = device.get("state", {})
                    current_state["status"] = "OFF"
                    requests.put(update_url, json={"state": current_state}, timeout=5)
                except:
                    pass

        return {
            "message": "Tenant successfully moved out. Devices switched to ECO mode.",
            "deleted_user_id": user_id,
            "devices_switched_off": len(devices)
        }, 200


api.add_resource(ArriveHomeResource, "/api/gateway/arrive-home")
api.add_resource(DashboardResource, "/api/gateway/dashboard/<string:user_id>")
api.add_resource(TenantMoveOutResource, "/api/gateway/tenant-move-out")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)