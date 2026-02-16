"""
DJ Playlist Optimizer - Flask Web App
Powered by GetSongBPM.com
"""

from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# TODO: Add your GetSongBPM API key here
API_KEY = 'YOUR_API_KEY_HERE'


class SongInfo:
    """Container for song data"""
    def __init__(self, title, artist, bpm=None, key=None, camelot=None):
        self.title = title
        self.artist = artist
        self.bpm = bpm
        self.key = key
        self.camelot = camelot
    
    def to_dict(self):
        return {
            'title': self.title,
            'artist': self.artist,
            'bpm': self.bpm,
            'key': self.key,
            'camelot': self.camelot
        }


def get_song_bpm_and_key(song_name, artist_name):
    """Fetch BPM and key from GetSongBPM API"""
    search_url = "https://api.getsongbpm.com/search/"
    
    search_params = {
        'api_key': API_KEY,
        'type': 'song',
        'lookup': f"{artist_name} {song_name}"
    }
    
    try:
        response = requests.get(search_url, params=search_params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'search' not in data or len(data['search']) == 0:
            return None
        
        song_id = data['search'][0].get('id')
        
        # Get detailed info
        detail_url = "https://api.getsongbpm.com/song/"
        detail_params = {'api_key': API_KEY, 'id': song_id}
        
        detail_response = requests.get(detail_url, params=detail_params, timeout=10)
        detail_response.raise_for_status()
        song_data = detail_response.json()
        
        if 'song' not in song_data:
            return None
        
        song = song_data['song']
        artist = song.get('artist', {})
        
        return SongInfo(
            title=song.get('title', song_name),
            artist=artist.get('name', artist_name),
            bpm=int(song.get('tempo')) if song.get('tempo') else None,
            key=song.get('key_of'),
            camelot=song.get('open_key')
        )
        
    except Exception as e:
        print(f"Error: {e}")
        return None


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze songs and return BPM/key data"""
    songs_input = request.json.get('songs', [])
    
    results = []
    for song_data in songs_input:
        song_name = song_data.get('title', '')
        artist_name = song_data.get('artist', '')
        
        if song_name and artist_name:
            song_info = get_song_bpm_and_key(song_name, artist_name)
            if song_info:
                results.append(song_info.to_dict())
            else:
                results.append({
                    'title': song_name,
                    'artist': artist_name,
                    'bpm': None,
                    'key': 'Not found',
                    'camelot': None
                })
    
    return jsonify({'songs': results})


if __name__ == '__main__':
    app.run(debug=True, port=5000)