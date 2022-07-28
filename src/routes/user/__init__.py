from src import app

@app.route('/')
def home():
    return {'Ping': 'Pong'}