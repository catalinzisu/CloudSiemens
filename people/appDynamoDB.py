from flask import Flask, request, send_from_directory
from flask_restful import Api, Resource
from botocore.exceptions import ClientError
from decimal import Decimal
import os
import uuid
from user import UserDAO

counter = 0

app = Flask('people')
api = Api(app)

# Initialize UserDAO
dao = UserDAO()

def _payload():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict() or {}


def _clean_item(item):
    return {k: v for k, v in item.items() if v is not None}


def _json_safe(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_safe(item) for item in sorted(value, key=str)]
    return value


class PeopleResource(Resource):
    def get(self):
        person_id = request.args.get('id')
        if person_id:
            user = dao.get_user_by_id(person_id)
            if not user:
                return {'error': 'Not found'}, 404
            return _json_safe(user)

        email = request.args.get('email')
        if email:
            user = dao.get_user_by_email(email)
            if not user:
                return {'error': 'Not found'}, 404
            return _json_safe(user)

        building_id = request.args.get('building_id')
        if building_id:
            users = dao.get_users_by_building(building_id)
            return _json_safe(users)

        users = dao.get_all_users()
        return _json_safe(users)

    def post(self):
        data = _payload()
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone = data.get('phone')
        dob = data.get('date_of_birth') or data.get('dob')
        building_id = data.get('building_id')
        apartment_number = data.get('apartment_number')
        role = data.get('role', 'TENANT')
        
        # Merge other fields into preferences if needed, or pass directly
        # Right now we let create_user handle defaults. 
        user = dao.create_user(first_name, last_name, email, phone, dob, building_id, apartment_number, role)
        
        if not user:
            return {'error': 'Failed to create user'}, 500

        return _json_safe(user), 201

    def put(self):
        person_id = request.args.get('id')
        if not person_id:
            return {'error': 'Invalid or missing id'}, 400

        data = _payload()
        
        # update_user handles the dict merging for preferences
        user = dao.update_user(person_id, data)
        if not user:
            return {'error': f'Missing person with id {person_id} or update failed'}, 404

        return _json_safe(user)

    def delete(self):
        person_id = request.args.get('id')
        if not person_id:
            return {'error': 'Invalid or missing id'}, 400
        
        # Ensure user exists before deleting
        existing = dao.get_user_by_id(person_id)
        if not existing:
            return {'error': f'Missing person with id {person_id}'}, 404

        success = dao.delete_user(person_id)
        if not success:
            return {'error': 'Failed to delete user'}, 500

        return {'status': 'OK'}


api.add_resource(PeopleResource, '/people')


@app.route('/count')
def count():
    global counter
    counter += 1
    return str(counter)


@app.route('/')
@app.route('/index')
def index():
    return send_from_directory(app.root_path, 'person.html')

@app.route('/health')
def health():
    return {'status': 'OK'}

@app.route('/doom')
@app.route('/doom/')
def doom():
    return send_from_directory(os.path.join(app.root_path, 'doom'), 'index.html')


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
