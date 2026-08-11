import os
import uuid
from datetime import datetime
from decimal import Decimal
from flask import Flask, request, send_from_directory
from flask_restful import Api, Resource
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

app = Flask("people")
api = Api(app)

dynamodb_endpoint = os.environ.get("DYNAMODB_ENDPOINT_URL")
if dynamodb_endpoint:
    dynamodb = boto3.resource('dynamodb', endpoint_url=dynamodb_endpoint, region_name=os.environ.get("AWS_DEFAULT_REGION", "eu-central-1"))
    dynamodb_client = boto3.client('dynamodb', endpoint_url=dynamodb_endpoint, region_name=os.environ.get("AWS_DEFAULT_REGION", "eu-central-1"))
else:
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get("AWS_DEFAULT_REGION", "eu-central-1"))
    dynamodb_client = boto3.client('dynamodb', region_name=os.environ.get("AWS_DEFAULT_REGION", "eu-central-1"))

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "users")

def initialize_database():
    try:
        dynamodb_client.describe_table(TableName=TABLE_NAME)
        print(f"Table {TABLE_NAME} already exists.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"Creating table {TABLE_NAME}...")
            dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                    {'AttributeName': 'email', 'AttributeType': 'S'},
                    {'AttributeName': 'building_id', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'email-index',
                        'KeySchema': [
                            {'AttributeName': 'email', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                    },
                    {
                        'IndexName': 'building-index',
                        'KeySchema': [
                            {'AttributeName': 'building_id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"Table {TABLE_NAME} created successfully.")
        else:
            print(f"Error checking table: {e}")

class UserDAO:
    def __init__(self):
        self.table = dynamodb.Table(TABLE_NAME)

    def create_user(self, first_name, last_name, email, phone, dob, building_id, apartment_number, role="TENANT"):
        try:
            user_id = str(uuid.uuid4())
            prefs = {'default_temperature': 22, 'auto_light': True}
            person = {
                'id': user_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'date_of_birth': dob,
                'role': role,
                'preferences': prefs,
                'created_at': datetime.now().isoformat()
            }
            if building_id is not None:
                person['building_id'] = str(building_id)
            if apartment_number is not None:
                person['apartment_number'] = int(apartment_number)
            
            # Remove None values
            person = {k: v for k, v in person.items() if v is not None}
            
            self.table.put_item(Item=person)
            return person
        except Exception as e:
            print(f"Error creating user: {e}", flush=True)
            return None

    def get_user_by_id(self, user_id: str):
        try:
            response = self.table.get_item(Key={'id': user_id})
            return response.get('Item')
        except Exception as e:
            print(f"Error getting user: {e}", flush=True)
            return None

    def get_all_users(self):
        try:
            response = self.table.scan()
            return response.get('Items', [])
        except Exception as e:
            print(f"Error scanning users: {e}", flush=True)
            return []

    def get_user_by_email(self, email: str):
        try:
            response = self.table.query(
                IndexName='email-index',
                KeyConditionExpression=Key('email').eq(email)
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error querying by email: {e}", flush=True)
            return None

    def get_users_by_building(self, building_id):
        try:
            response = self.table.query(
                IndexName='building-index',
                KeyConditionExpression=Key('building_id').eq(str(building_id))
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error querying by building: {e}", flush=True)
            return []

    def update_user(self, user_id: str, updates: dict):
        if not updates:
            return None
        person = self.get_user_by_id(user_id)
        if not person:
            return None

        if 'preferences' in updates and isinstance(updates['preferences'], dict):
            current_prefs = person.get('preferences', {})
            new_prefs = dict(current_prefs)
            new_prefs.update(updates['preferences'])
            person['preferences'] = new_prefs

        for field, value in updates.items():
            if field in ('id', 'preferences'):
                continue
            person[field] = value
            
        try:
            self.table.put_item(Item=person)
            return person
        except Exception as e:
            print(f"Error updating user: {e}", flush=True)
            return None

    def delete_user(self, user_id: str):
        try:
            self.table.delete_item(Key={'id': user_id})
            return True
        except Exception as e:
            print(f"Error deleting user: {e}", flush=True)
            return False

dao = UserDAO()

def _payload():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict() or {}

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

        return _json_safe(dao.get_all_users())

    def post(self):
        data = _payload()
        if not data or (not data.get('first_name') and not data.get('email')):
            return {'error': 'Missing required fields (first_name or email)'}, 400
        user = dao.create_user(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            dob=data.get('date_of_birth') or data.get('dob'),
            building_id=data.get('building_id'),
            apartment_number=data.get('apartment_number'),
            role=data.get('role', 'TENANT')
        )
        if not user:
            return {'error': 'Failed to create user'}, 500
        return _json_safe(user), 201

    def put(self):
        person_id = request.args.get('id')
        if not person_id:
            return {'error': 'Invalid or missing id'}, 400
        data = _payload()
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
            return {'error': 'Not found'}, 404
        success = dao.delete_user(person_id)
        if not success:
            return {'error': 'Not found'}, 404
        return {'status': 'OK'}

api.add_resource(PeopleResource, '/people')

counter = 0

@app.route('/count')
def count():
    global counter
    counter += 1
    return str(counter)

@app.route('/')
@app.route('/index')
def index():
    return send_from_directory(os.path.join(app.root_path, '..'), 'person.html')

@app.route('/health')
def health():
    return {'status': 'OK'}

@app.route('/doom')
@app.route('/doom/')
def doom_page():
    return send_from_directory(os.path.join(app.root_path, '..', 'doom'), 'index.html')

if __name__ == '__main__':
    initialize_database()
    app.run('0.0.0.0', port=5000, debug=True)
