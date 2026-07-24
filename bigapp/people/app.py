from flask import Flask, request
from dataclasses import dataclass, asdict
from flask_restful import *
import os

from flask_sqlalchemy import SQLAlchemy

counter = 0

app = Flask('people')
api = Api(app)

# TODO: can be improved, security wise
db_user = os.environ.get('DB_USER') or 'siemens'
db_pass = os.environ.get('DB_PASS') or 'abc123'
db_host = os.environ.get('DB_HOST') or 'catalin-db.summer24.net'
db_name = os.environ.get('DB_NAME') or 'bigapp'
db_port = os.environ.get('DB_PORT') or '3306'

# Am schimbat mysql:// in mysql+pymysql://
db_url = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}:{int(db_port)}/{db_name}'
#db_url = f'mysql://{db_user}:{db_pass}@{db_host}:{int(db_port)}/{db_name}'

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
db = SQLAlchemy(app)

# @dataclass
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # int not null auto_increement
    first_name = db.Column(db.String(128))  # VARCHAR(128)
    last_name = db.Column(db.String(128))
    email = db.Column(db.String(256))

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if '_state' not in k}

def _to_int(s, default=None) -> int:
    if s is None:
        return default
    try:
        val = int(s.strip())
        return val
    except Exception as e:
        return default

class PeopleResource(Resource):
    def get(self):
        id = _to_int(request.args.get('id'))
        if id:
            p = db.session.query(Person).filter(Person.id == id).first()
            if p:
                return p.to_dict()
            return {'error': 'Not found'}, 404
        people = db.session.query(Person).all()
        return [p.to_dict() for p in people]

    def post(self):
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        p = Person(first_name=first_name,
                   last_name=last_name, email=email)
        try:
            db.session.add(p)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
        return 'OK'

    def put(self):
        id = _to_int(request.args.get('id'))
        if not id:
            return {'error': 'Invalid or missing id'}, 401
        p = db.session.query(Person).filter(Person.id == id).first()
        if not p:
            return {'error': f'Missing person with id {id}'}, 401
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        p.first_name = first_name
        p.last_name = last_name
        p.email = email
        db.session.commit()
        return 'OK'

    def delete(self):
        id = _to_int(request.args.get('id'))
        if not id:
            # 400 este codul HTTP corect pentru "Bad Request" (cerere invalidă)
            return {'error': 'Invalid or missing id'}, 400
        
        p = db.session.query(Person).filter(Person.id == id).first()
        if not p:
            # 404 este codul HTTP pentru "Not Found"
            return {'error': f'Missing person with id {id}'}, 404
            
        try:
            db.session.delete(p)
            db.session.commit()
            return {'message': f'Person with id {id} was deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to delete person from database'}, 500

api.add_resource(PeopleResource, '/people')


@app.route('/count')
def count():
    global counter
    counter += 1
    return str(counter)

@app.route('/')
@app.route('/index')
def index():
    return '<html><body><h1>Hello world!</h1></body></html>\n'

# Creeaza tabelele pe baza definitiei Python
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
