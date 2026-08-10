import os
from dataclasses import dataclass

from flask import Flask, request, send_from_directory
from flask_restful import *
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask("people")
api = Api(app)

db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASS")
db_host = os.environ.get("DB_HOST")
db_name = os.environ.get("DB_NAME")
db_port = os.environ.get("DB_PORT") or "3306"

db_url = f"mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config["SQLALCHEMY_DATABASE_URI"] = db_url

db = SQLAlchemy(app)

counter = 0


@dataclass
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(128))
    last_name = db.Column(db.String(128))
    email = db.Column(db.String(256))
    building_id = db.Column(db.Integer)
    apartment_nr = db.Column(db.Integer)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if "_state" not in k}


class PeopleResource(Resource):
    def get(self):
        id = request.args.get("id")
        if id:
            try:
                id = int(id.strip())
                person = db.session.query(Person).filter(Person.id == id).first()
                if person:
                    return person.to_dict()
                return {"error": "Invalid id"}, 404
            except ValueError:
                return {"error": "Invalid id"}, 400
        people = db.session.query(Person).all()
        return [person.to_dict() for person in people]

    def post(self):
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        person = Person(first_name=first_name, last_name=last_name, email=email, building_id=1, apartment_nr=1)
        db.session.add(person)
        db.session.commit()
        return person.to_dict(), 201

    def put(self):
        id = request.form.get("id")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        building_id = request.form.get("building_id")
        apartment_nr = request.form.get("apartment_nr")
        person = db.session.query(Person).filter(Person.id == id).first()
        if person:
            person.first_name = first_name
            person.last_name = last_name
            person.email = email
            person.building_id = building_id
            person.apartment_nr = apartment_nr
            db.session.commit()
            return person.to_dict(), 201
        return {"error": "Person not found"}, 404

    def delete(self):
        id = request.args.get("id")
        person = db.session.query(Person).filter(Person.id == id).first()
        if person:
            db.session.delete(person)
            db.session.commit()
            return person.to_dict(), 201
        return {"error": "Person not found"}, 404


api.add_resource(PeopleResource, "/people")


@app.route("/")
@app.route("/index")
def index():
    return "<html><body><h1>Hello world!</h1></body></html>\n"


@app.route("/person")
def person_page():
    return send_from_directory(BASE_DIR, "person.html")


@app.route("/doom")
def doom_page():
    return send_from_directory(BASE_DIR, "doom.html")


@app.route("/count")
def count():
    global counter
    counter += 1
    return str(counter)


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
