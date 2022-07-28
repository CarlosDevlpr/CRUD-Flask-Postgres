from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

app = Flask(__name__)
db = SQLAlchemy()
cors = CORS(app)

db.init_app(app)
Migrate(app, db)

load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['CORS_HEADERS'] = os.getenv('CORS_HEADERS')

from src.routes.user import *
from src.models.user import UsersTable

@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db, User=UsersTable)