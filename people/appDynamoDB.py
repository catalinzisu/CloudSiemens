from flask import Flask, request, send_from_directory
from flask_restful import Api, Resource
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal
import os
import uuid

counter = 0

app = Flask('people')
api = Api(app)

aws_region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'ap-northeast-3'
table_name = os.environ.get('DYNAMODB_TABLE') or 'users'

dynamodb = boto3.resource('dynamodb', region_name=aws_region)
table = dynamodb.Table(table_name)


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


def _get_person(person_id):
    try:
        response = table.get_item(Key={'id': person_id})
    except ClientError as exc:
        return None, {'error': str(exc)}, 500
    return response.get('Item'), None, None


class PeopleResource(Resource):
    def get(self):
        person_id = request.args.get('id')
        if person_id:
            item, error_body, status = _get_person(person_id)
            if error_body:
                return error_body, status
            if not item:
                return {'error': 'Not found'}, 404
            return _json_safe(item)

        try:
            response = table.scan()
            items = response.get('Items', [])
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))
        except ClientError as exc:
            return {'error': str(exc)}, 500

        return _json_safe(items)

    def post(self):
        data = _payload()
        item = _clean_item({
            'id': str(uuid.uuid4()),
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'email': data.get('email'),
        })

        try:
            table.put_item(Item=item)
        except ClientError as exc:
            return {'error': str(exc)}, 500

        return _json_safe(item), 201

    def put(self):
        person_id = request.args.get('id')
        if not person_id:
            return {'error': 'Invalid or missing id'}, 400

        existing, error_body, status = _get_person(person_id)
        if error_body:
            return error_body, status
        if not existing:
            return {'error': f'Missing person with id {person_id}'}, 404

        data = _payload()
        updates = {}
        for field in ('first_name', 'last_name', 'email'):
            if field in data and data[field] is not None:
                updates[field] = data[field]

        if not updates:
            return {'error': 'No fields to update'}, 400

        expression_parts = []
        expression_values = {}
        for field, value in updates.items():
            placeholder = f':{field}'
            expression_parts.append(f'{field} = {placeholder}')
            expression_values[placeholder] = value

        try:
            response = table.update_item(
                Key={'id': person_id},
                UpdateExpression='SET ' + ', '.join(expression_parts),
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW',
            )
        except ClientError as exc:
            return {'error': str(exc)}, 500

        return _json_safe(response.get('Attributes', existing))

    def delete(self):
        person_id = request.args.get('id')
        if not person_id:
            return {'error': 'Invalid or missing id'}, 400

        existing, error_body, status = _get_person(person_id)
        if error_body:
            return error_body, status
        if not existing:
            return {'error': f'Missing person with id {person_id}'}, 404

        try:
            table.delete_item(Key={'id': person_id})
        except ClientError as exc:
            return {'error': str(exc)}, 500

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
