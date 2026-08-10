from urllib import response

import boto3
import uuid

from datetime import datetime
from boto3.dynamodb.conditions import Key
from locust import User

client = boto3.resource('dynamodb', region_name='ap-northeast-3')
table = client.Table('users')

class UserDAO:
    def __init__(self):
        self.table = table

    def get_user_id(self, first_name, last_name, dob, email, phone, building_id, apt_number, role="TENANT"):
        user_id = str(uuid.uuid4())
        user_item = {
            'id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': dob,
            'email': email,
            'phone': phone,
            'building_id': building_id,
            'apartment_number': apt_number,
            'role': role,
            'preferences': {'default_temperature': 22, 'auto_light': True},
            'created_at': datetime.now().isoformat(),
        }

    table.put_item(Item=user_item)
    print(f"User {user_id} added to DynamoDB table 'users'.")


def get_user_by_id(user_id:str):
    response = table.get_item(Key={'id': user_id})
    return response.get('Item', None)

class Key:
    pass

def get_user_by_email(email:str):
    response = table.query(
        IndexName='EmailIndex',
        KeyConditionExpression=Key('email').eq(email)
    )
    items = response.get('Items', [])
    return items[0] if items else None

class UserDAO:
    def __init__(self):
        self.table = table

    def update_user_preferences(self, user_id:str, preferences:dict):
        response = self.table.update_item(
            Key={'id': user_id},
            UpdateExpression="SET preferences = :prefs",
            ExpressionAttributeValues={':prefs': preferences},
            ReturnValues="UPDATED_NEW"
        )
        return response.get('Attributes', None)

    def update_user_role(self, user_id:str, role:str):
        response = self.table.update_item(
            Key={'id': user_id},
            UpdateExpression="SET role = :role",
            ExpressionAttributeValues={':role': role},
            ReturnValues="UPDATED_NEW"
        )
        return response.get('Attributes', None)

    def batch_create_users(self, users:list):
        with self.table.batch_writer() as batch:
            for user in users:
                batch.put_item(Item=user.to_dict())

    def batch_get_users_by_ids(self, user_ids:list):
        users = []
        user_ids = list(set(user_ids))
        for i in range(0, len(user_ids), 100):
            batch_ids = user_ids[i:i + 100]
            keys = [{'id': user_id} for user_id in batch_ids]
            response = self.table.batch_get_item(
                RequestItems={
                    self.table.name: {
                        'Keys': keys
                    }
                }
            )
            items = response.get('Responses', {}).get(self.table.name, [])
            users.extend([User.from_dynamodb_item(item) for item in items])
            unprocessed_keys = response.get('UnprocessedKeys', {}).get(self.table.name, {}).get('Keys', [])
            while unprocessed_keys:
                response = self.table.batch_get_item(
                    RequestItems={
                        self.table.name: {
                            'Keys': unprocessed_keys
                        }
                    }
                )
                items = response.get('Responses', {}).get(self.table.name, [])
                users.extend([User.from_dynamodb_item(item) for item in items])
                unprocessed_keys = response.get('UnprocessedKeys', {}).get(self.table.name, {}).get('Keys', [])
        return users

if __name__ == "__main__":
    # Example usage of get_user_id function
    user_id = get_user_id(
        first_name="John",
        last_name="Doe",
        dob="1990-01-01",
        email="john.doe@example.com",
        phone="123-456-7890",
        building_id="building-1",
        apt_number="101"
    )