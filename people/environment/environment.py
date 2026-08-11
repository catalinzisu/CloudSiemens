import os
import uuid
import requests
from flask import Flask, request
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy

app = Flask("environment")
api = Api(app)

db_user = os.environ.get("DB_USER", "gigi")
db_password = os.environ.get("DB_PASS", "abc123")
db_host = os.environ.get("DB_HOST", "people-db")
db_name = os.environ.get("DB_NAME", "bigapp")
db_port = os.environ.get("DB_PORT", "3306")

db_url = f"mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.String(36), primary_key=True)
    building_id = db.Column(db.String(64), index=True)
    apartment_number = db.Column(db.Integer)
    device_type = db.Column(db.String(64))
    state = db.Column(db.JSON)
    energy_consumption = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

def _payload():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict() or {}

class SyncPreferencesResource(Resource):
    def post(self):
        data = _payload()
        user_id = data.get("user_id")
        if not user_id:
            return {"error": "Missing user_id"}, 400

        # Apelam serviciul de Users pentru a afla setarile
        people_service_url = f"http://people:5000/people?id={user_id}"
        try:
            response = requests.get(people_service_url, timeout=5)
            if response.status_code != 200:
                return {"error": f"Failed to fetch user from people service (status {response.status_code})"}, 500
            user_data = response.json()
        except Exception as e:
            print(f"Error calling people service: {e}", flush=True)
            return {"error": "Failed to connect to people service"}, 500

        # Daca response e dict cu eroare in loc de model
        if "error" in user_data:
            return {"error": user_data["error"]}, 400

        building_id = user_data.get("building_id")
        apartment_number = user_data.get("apartment_number")
        preferences = user_data.get("preferences") or {}

        if not building_id or apartment_number is None:
            return {"error": "User does not have a building_id or apartment_number assigned"}, 400

        default_temp = preferences.get("default_temperature", 22)
        auto_light = preferences.get("auto_light", True)

        # Cautam daca exista deja dispozitive in apartament
        devices = Device.query.filter_by(
            building_id=str(building_id), 
            apartment_number=int(apartment_number)
        ).all()

        thermostat = next((d for d in devices if d.device_type == "THERMOSTAT"), None)
        light = next((d for d in devices if d.device_type == "LIGHT"), None)

        if not thermostat:
            thermostat = Device(
                id=str(uuid.uuid4()),
                building_id=str(building_id),
                apartment_number=int(apartment_number),
                device_type="THERMOSTAT",
                state={"status": "ON", "value": default_temp},
                energy_consumption=1.5 # Simulam un consum in kWh
            )
            db.session.add(thermostat)
        else:
            state = dict(thermostat.state or {})
            state["value"] = default_temp
            thermostat.state = state

        if not light:
            light = Device(
                id=str(uuid.uuid4()),
                building_id=str(building_id),
                apartment_number=int(apartment_number),
                device_type="LIGHT",
                state={"status": "ON" if auto_light else "OFF"},
                energy_consumption=0.06 # Consum in kWh pentru un bec
            )
            db.session.add(light)
        else:
            state = dict(light.state or {})
            state["status"] = "ON" if auto_light else "OFF"
            light.state = state

        try:
            db.session.commit()
            # Fortam accesarea pentru a nu avea Dictionar gol dupa commit
            t_dict = {c.name: getattr(thermostat, c.name) for c in thermostat.__table__.columns}
            l_dict = {c.name: getattr(light, c.name) for c in light.__table__.columns}
            return {
                "message": "Preferences synced successfully",
                "devices": [t_dict, l_dict]
            }, 200
        except Exception as e:
            db.session.rollback()
            print(f"Error saving to db: {e}", flush=True)
            return {"error": f"Database error: {e}"}, 500

class EnvironmentStatusResource(Resource):
    def get(self):
        building_id = request.args.get("building_id")
        apartment_number = request.args.get("apartment_number")

        if not building_id or apartment_number is None:
            return {"error": "Missing building_id or apartment_number"}, 400

        devices = Device.query.filter_by(
            building_id=str(building_id), 
            apartment_number=int(apartment_number)
        ).all()
        
        return [d.to_dict() for d in devices], 200

class EnvironmentDeviceResource(Resource):
    def put(self, device_id):
        data = _payload()
        new_state = data.get("state")
        
        if not new_state:
            return {"error": "Missing state payload"}, 400

        device = Device.query.get(device_id)
        if not device:
            return {"error": "Device not found"}, 404

        current_state = device.state or {}
        updated_state = dict(current_state)
        updated_state.update(new_state)
        device.state = updated_state

        try:
            db.session.commit()
            return {c.name: getattr(device, c.name) for c in device.__table__.columns}, 200
        except Exception as e:
            db.session.rollback()
            print(f"Error updating device: {e}", flush=True)
            return {"error": str(e)}, 500

class EnvironmentEnergyReportResource(Resource):
    def get(self, building_id):
        devices = Device.query.filter_by(building_id=str(building_id)).all()
        
        total_consumption = 0.0
        apartments = {}

        for d in devices:
            is_on = True
            if isinstance(d.state, dict):
                is_on = d.state.get("status", "ON") == "ON"
            
            consumption = float(d.energy_consumption or 0)
            if not is_on:
                consumption *= 0.1 # Putere in Standby cand e oprit

            total_consumption += consumption
            apt = d.apartment_number
            apartments[apt] = apartments.get(apt, 0.0) + consumption
            
        return {
            "building_id": building_id,
            "total_estimated_kwh": total_consumption,
            "apartments_breakdown": apartments
        }, 200

api.add_resource(SyncPreferencesResource, "/environment/sync-preferences")
api.add_resource(EnvironmentStatusResource, "/environment/status")
api.add_resource(EnvironmentDeviceResource, "/environment/device/<string:device_id>")
api.add_resource(EnvironmentEnergyReportResource, "/environment/building/<string:building_id>/energy-report")

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)