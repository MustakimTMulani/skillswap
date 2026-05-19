from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(100),
        nullable=False
    )

    qualification = db.Column(
        db.String(200)
    )

    bio = db.Column(
        db.String(500)
    )

    contact = db.Column(
        db.String(100)
    )


class Skill(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    skill_name = db.Column(db.String(100), nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

class Request(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(
        db.Integer,
        nullable=False
    )

    receiver_id = db.Column(
        db.Integer,
        nullable=False
    )

    skill_id = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default='Pending'
    )

class Message(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    request_id = db.Column(
        db.Integer,
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        nullable=False
    )

    text = db.Column(
        db.String(500),
        nullable=False
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class Rating(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    receiver_id = db.Column(
        db.Integer,
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        nullable=False
    )

    rating = db.Column(
        db.Integer,
        nullable=False
    )

    feedback = db.Column(
        db.String(500),
        nullable=False
    )