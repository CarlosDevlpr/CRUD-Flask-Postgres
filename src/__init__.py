from flask import Flask

app = Flask(__name__)

from src.routes.user import *

@app.shell_context_processor
def make_shell_context():
    return dict(app=app)