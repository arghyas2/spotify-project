from flask import Flask, send_file, jsonify, render_template
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

global client_id
client_id = os.environ.get('CLIENT_ID')

print(client_id)

global client_secret
client_secret = os.environ.get('CLIENT_SECRET')

print(client_secret)

global redirect_uri
redirect_uri = os.environ.get('REDIRECT_URI')

global login
login = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    global client_secret, client_id

    return '', 200

@app.route('/callback')
def callback():
    return '', 200

if __name__ == '__main__':
    app.run(debug=True, port=34000)