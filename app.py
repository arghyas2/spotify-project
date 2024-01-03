from flask import Flask, send_file, jsonify, render_template, redirect, request, session
from spotipy.oauth2 import SpotifyOAuth
import os, spotipy, requests, geohash2
from dotenv import load_dotenv
from geopy.geocoders import Nominatim

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
app.secret_key = os.getenv('SECRET_KEY')

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
    return render_template('callback.html'), 200

@app.route('/findEvents', methods=['GET'])
def find_events(): #find events based on the user's top 5 artists in the medium term
    top_artists = find_top_artists(5)
    events_info = {}
    for artist in top_artists:
        attractionId = find_attraction_id(artist)
        if not attractionId:
            continue
        # latlong = f'{session["lat"]},{session["long"]}'
        params = {'apikey':app.config['tm_key'], 'attractionId':attractionId}
        json = requests.get(url=app.config['tm_root_url'] + 'events.json', params=params).json()
        embedded = json.get('_embedded', None)
        if not embedded:
            events_info[artist] = None
        else:
            events = embedded.get('events', None)
            if not events:
                events_info[artist] = None
            else:
                events_info[artist] = []
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

def find_attraction_id(artist: str):
    params = {'apikey':app.config['tm_key'], "keyword":artist}
    r = requests.get(url=app.config['tm_root_url'] + 'attractions.json', params=params)
    data = r.json()
    attractions = data['_embedded']['attractions']
    for attraction in attractions:
        if str(attraction['name']).lower() == artist.lower():
            return attraction['id']
    return None

if __name__ == '__main__':
    app.run(debug=True, port=34000)