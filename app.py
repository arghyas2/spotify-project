from flask import Flask, jsonify, redirect, request, session
from spotipy.oauth2 import SpotifyOAuth
from flask_cors import CORS
from flask_session import Session
import os, spotipy, requests
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv('CLIENT_ID')

client_secret = os.getenv('CLIENT_SECRET')

redirect_uri = os.getenv('REDIRECT_URI')

scope = os.getenv('SCOPE')

tm_key = os.getenv('CONSUMER_KEY')

tm_root_url = "https://app.ticketmaster.com/discovery/v2/"

o_auth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope)

app = Flask(__name__)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['tm_root_url'] = tm_root_url
app.config['tm_key'] = tm_key
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.secret_key = os.getenv('SECRET_KEY')

Session(app)
CORS(app, resources={r"/*": {"origins": ["https://localhost:3000"]}}, supports_credentials=True)

@app.route('/')
def index():
    return 'Hi', 200

@app.route('/login')
def authorize():
    global o_auth
    auth_url = o_auth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    response = list(request.args.items())
    if response[0][1] == 'access_denied':
        return 'Thank you for giving the app a try!', 200
    
    code = request.args.get('code')

    if not code:
        return "Didn't receive authorization code. ERROR", 400
    
    token_info = o_auth.get_access_token(code)
    auth = ''
    if type(token_info == dict):
        auth = token_info["access_token"]
    else:
        auth = token_info
    
    session['auth'] = auth
    return redirect(os.getenv('REACT_UTILITIES_URL')), 200

@app.route('/findEvents', methods=['GET'])
def find_events(): #find events based on the user's top 5 artists in the medium term
    top_artists = find_top_artists(5)
    events_info = {}
    for artist in top_artists:
        events_info[artist] = [{'image':find_artist_image(artist), 'found':False}]
        attractionId = find_attraction_id(artist)
        if not attractionId:
            continue
        # latlong = f'{session["lat"]},{session["long"]}'
        # latlon = str(session['lat']) + ',' + str(session['long'])
        # print(latlon)
        params = {'apikey':app.config['tm_key'], 'attractionId':attractionId} #, 'latlon':latlon, 'radius':500}
        json = requests.get(url=app.config['tm_root_url'] + 'events.json', params=params).json()
        embedded = json.get('_embedded', None)
        if embedded:
            events = embedded.get('events', None)
            if events:
                events_info[artist][0]['found'] = True
                for event in events:
                    to_append = {}
                    to_append['name'] = event.get('name', None)
                    to_append['date'] = event['dates']['start'].get('localDate', 'TBD')
                    to_append['time'] = event['dates']['start'].get('localTime', 'TBD')
                    price_info = event.get('priceRanges', [{'currency': 'USD', 'min': 'TBD', 'max': 'TBD'}])[0]
                    to_append['std_price'] = {'currency':price_info['currency'], 'min':price_info['min'], 'max':price_info['max']}
                    to_append['ticket_url'] = event.get('url', None)
                    venue_info = event.get('_embedded', {'venues': [{'name':'TBD', 'city':'TBD', 'country':'TBD'}]})['venues'][0]
                    to_append['location'] = {'name':venue_info['name'], 'city':venue_info['city']['name'], 'country':venue_info['country']['name']}
                    events_info[artist].append(to_append)
    return jsonify(events_info), 200 

@app.route('/saveLocation', methods=['POST'])
def save_location():
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    # Save latitude and longitude in the session
    session['lat'] = latitude
    session['long'] = longitude

    return jsonify({'message': 'Location saved successfully'}), 200

def find_top_artists(n: int) -> list:
    sp = spotipy.Spotify(auth=session['auth'])
    top_artists = sp.current_user_top_artists(limit=n, offset=0, time_range='medium_term')
    artists = top_artists['items']
    to_return = []
    for artist in artists:
        to_return.append(artist['name'])
    return to_return

def find_artist_image(name: str) -> str:
    spotify = spotipy.Spotify(auth=session['auth'])
    results = spotify.search(q='artist:' + name, type='artist')
    items = results['artists']['items']
    if len(items) > 0:
        artist = items[0]
        return artist['images'][0]['url']
    return None

def find_attraction_id(artist: str) -> str:
    params = {'apikey':app.config['tm_key'], "keyword":artist}
    r = requests.get(url=app.config['tm_root_url'] + 'attractions.json', params=params)
    data = r.json()
    attractions = data['_embedded']['attractions']
    for attraction in attractions:
        if str(attraction['name']).lower() == artist.lower():
            return attraction['id']
    return None

if __name__ == '__main__':
    app.run(debug=True, ssl_context=('cert.pem', 'key.pem'), port=34000)