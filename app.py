"""
DJ Playlist Optimizer - Flask Web App
Powered by MusicBrainz + AcousticBrainz (no API key required)
"""

from flask import Flask, render_template, request, jsonify
import requests
import time

app = Flask(__name__)

# In-memory storage for master song list
master_song_list = []

# MusicBrainz requires a descriptive User-Agent or requests get blocked
# TODO: Replace 'your@email.com' with your actual email address
MUSICBRAINZ_HEADERS = {
    'User-Agent': 'DJPlaylistOptimizer/1.0 (carterad@umich.edu)'
}


class SongInfo:
    """Container for song data"""
    def __init__(self, title, artist, tempo=None, key=None, camelot=None, genre=''):
        self.title = title
        self.artist = artist
        self.tempo = tempo
        self.key = key
        self.camelot = camelot
        self.genre = genre

    def to_dict(self):
        return {
            'title': self.title,
            'artist': self.artist,
            'tempo': self.tempo,
            'key': self.key,
            'camelot': self.camelot,
            'genre': self.genre
        }


# Camelot wheel lookup: (key_name, scale) -> camelot notation
CAMELOT = {
    ('C', 'major'): '8B',  ('C', 'minor'): '5A',
    ('C#', 'major'): '3B', ('C#', 'minor'): '12A',
    ('D', 'major'): '10B', ('D', 'minor'): '7A',
    ('D#', 'major'): '5B', ('D#', 'minor'): '2A',
    ('E', 'major'): '12B', ('E', 'minor'): '9A',
    ('F', 'major'): '7B',  ('F', 'minor'): '4A',
    ('F#', 'major'): '2B', ('F#', 'minor'): '11A',
    ('G', 'major'): '9B',  ('G', 'minor'): '6A',
    ('G#', 'major'): '4B', ('G#', 'minor'): '1A',
    ('A', 'major'): '11B', ('A', 'minor'): '8A',
    ('A#', 'major'): '6B', ('A#', 'minor'): '3A',
    ('B', 'major'): '1B',  ('B', 'minor'): '10A',
}

# AcousticBrainz uses flat notation sometimes, normalize to sharps
FLAT_TO_SHARP = {
    'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#',
    'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B'
}


def get_song_bpm_and_key(song_name, artist_name):
    """
    Fetch BPM and key using MusicBrainz (to find MBID) + AcousticBrainz (for audio data).
    No API key required.
    """
    try:
        # Step 1: Search MusicBrainz for the recording to get its MBID
        search_url = 'https://musicbrainz.org/ws/2/recording/'
        search_params = {
            'query': f'recording:"{song_name}" AND artist:"{artist_name}"',
            'fmt': 'json',
            'limit': 5
        }

        search_response = requests.get(
            search_url,
            params=search_params,
            headers=MUSICBRAINZ_HEADERS,
            timeout=10
        )
        search_response.raise_for_status()
        search_data = search_response.json()

        recordings = search_data.get('recordings', [])
        if not recordings:
            print(f"MusicBrainz: No results for {song_name} by {artist_name}")
            return None

        # Pick the first result and grab its MBID
        mbid = recordings[0].get('id')
        found_title = recordings[0].get('title', song_name)
        found_artist = artist_name
        if recordings[0].get('artist-credit'):
            found_artist = recordings[0]['artist-credit'][0].get('artist', {}).get('name', artist_name)

        # MusicBrainz rate limit: max 1 request/second for unauthenticated users
        time.sleep(1)

        # Step 2: Query AcousticBrainz for audio features using the MBID
        ab_url = f'https://acousticbrainz.org/{mbid}/low-level'
        ab_response = requests.get(ab_url, timeout=10)

        if ab_response.status_code == 404:
            print(f"AcousticBrainz: No data for MBID {mbid}")
            return None

        ab_response.raise_for_status()
        ab_data = ab_response.json()

        # Extract BPM
        tempo = ab_data.get('rhythm', {}).get('bpm')

        # Extract key and scale
        tonal = ab_data.get('tonal', {})
        key_name = tonal.get('key_key')   # e.g. "C", "F#", "Bb"
        scale = tonal.get('key_scale')    # "major" or "minor"

        # Normalize flat notation to sharp
        if key_name in FLAT_TO_SHARP:
            key_name = FLAT_TO_SHARP[key_name]

        # Build display key string (e.g. "C# minor")
        key_display = f"{key_name} {scale}" if key_name and scale else None

        # Look up Camelot notation
        camelot = CAMELOT.get((key_name, scale)) if key_name and scale else None

        return SongInfo(
            title=found_title,
            artist=found_artist,
            tempo=round(tempo) if tempo else None,
            key=key_display,
            camelot=camelot,
            genre=''
        )

    except Exception as e:
        print(f"Error fetching song data: {e}")
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/add', methods=['POST'])
def add_song():
    """Add songs to the master list"""
    songs_input = request.json.get('songs', [])

    results = []
    for song_data in songs_input:
        song_name = song_data.get('title', '')
        artist_name = song_data.get('artist', '')

        if song_name and artist_name:
            song_info = get_song_bpm_and_key(song_name, artist_name)
            if song_info:
                song_dict = song_info.to_dict()
            else:
                song_dict = {
                    'title': song_name,
                    'artist': artist_name,
                    'tempo': None,
                    'key': 'Not found',
                    'camelot': None,
                    'genre': ''
                }

            if not any(s['title'] == song_dict['title'] and s['artist'] == song_dict['artist'] for s in master_song_list):
                master_song_list.append(song_dict)
            results.append(song_dict)

    return jsonify({'songs': results})


@app.route('/upload_txt', methods=['POST'])
def upload_txt():
    """Upload and parse a txt file with songs in 'Title | Artist' format"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not file.filename.endswith('.txt'):
        return jsonify({'success': False, 'error': 'Only .txt files are allowed'}), 400

    try:
        content = file.read().decode('utf-8')
        lines = content.strip().split('\n')

        songs_to_add = []
        for line in lines:
            line = line.strip()
            if not line or '|' not in line:
                continue
            parts = line.split('|')
            if len(parts) >= 2:
                title = parts[0].strip()
                artist = parts[1].strip()
                if title and artist:
                    songs_to_add.append({'title': title, 'artist': artist})

        results = []
        skipped = []
        for song_data in songs_to_add:
            song_name = song_data['title']
            artist_name = song_data['artist']

            song_info = get_song_bpm_and_key(song_name, artist_name)
            if song_info:
                song_dict = song_info.to_dict()
                if not any(s['title'] == song_dict['title'] and s['artist'] == song_dict['artist'] for s in master_song_list):
                    master_song_list.append(song_dict)
                results.append(song_dict)
            else:
                skipped.append({'title': song_name, 'artist': artist_name})

        return jsonify({
            'success': True,
            'added': len(results),
            'skipped': len(skipped),
            'skipped_songs': skipped,
            'songs': results,
            'master_list': master_song_list
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def key_distance(camelot1, camelot2):
    if not camelot1 or not camelot2:
        return 6
    try:
        num1 = int(''.join(filter(str.isdigit, camelot1)))
        letter1 = ''.join(filter(str.isalpha, camelot1)).upper()
        num2 = int(''.join(filter(str.isdigit, camelot2)))
        letter2 = ''.join(filter(str.isalpha, camelot2)).upper()
    except:
        return 6

    if num1 == num2 and letter1 == letter2:
        return 0
    if num1 == num2:
        return 1

    wheel_distance = min(abs(num1 - num2), 12 - abs(num1 - num2))
    if wheel_distance == 1 and letter1 == letter2:
        return 1

    letter_penalty = 0 if letter1 == letter2 else 1
    return wheel_distance + letter_penalty


def distance(SONG1, SONG2):
    tempo_diff1 = abs(SONG1.tempo - SONG2.tempo) if SONG1.tempo and SONG2.tempo else 100
    tempo_diff2 = abs(SONG1.tempo - 2 * SONG2.tempo) if SONG1.tempo and SONG2.tempo else 100
    tempo_diff3 = abs(2 * SONG1.tempo - SONG2.tempo) if SONG1.tempo and SONG2.tempo else 100
    return min(tempo_diff1, tempo_diff2, tempo_diff3) + 4.0 * abs(key_distance(SONG1.camelot, SONG2.camelot))


def make_End_list(Song_List):
    if not Song_List or len(Song_List) <= 1:
        return Song_List

    def dict_to_songinfo(song_dict):
        s = SongInfo(
            title=song_dict.get('title', ''),
            artist=song_dict.get('artist', ''),
            tempo=song_dict.get('tempo'),
            key=song_dict.get('key'),
            camelot=song_dict.get('camelot'),
            genre=song_dict.get('genre', '')
        )
        return s

    song_objects = [dict_to_songinfo(s) for s in Song_List]

    unvisited = set(range(len(song_objects)))
    current = 0
    tour = [current]
    unvisited.remove(current)

    while unvisited:
        nearest = min(unvisited, key=lambda i: distance(song_objects[current], song_objects[i]))
        tour.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    improved = True
    while improved:
        improved = False
        for i in range(1, len(tour) - 2):
            for j in range(i + 1, len(tour)):
                if j - i == 1:
                    continue
                current_dist = (distance(song_objects[tour[i-1]], song_objects[tour[i]]) +
                                distance(song_objects[tour[j-1]], song_objects[tour[j % len(tour)]]))
                new_dist = (distance(song_objects[tour[i-1]], song_objects[tour[j-1]]) +
                            distance(song_objects[tour[i]], song_objects[tour[j % len(tour)]]))
                if new_dist < current_dist:
                    tour[i:j] = reversed(tour[i:j])
                    improved = True
                    break
            if improved:
                break

    return [Song_List[i] for i in tour]


def add_song_after(optimized_list, new_song):
    if not optimized_list:
        return [new_song]
    if len(optimized_list) == 1:
        return optimized_list + [new_song]

    def dict_to_songinfo(song_dict):
        return SongInfo(
            title=song_dict.get('title', ''),
            artist=song_dict.get('artist', ''),
            tempo=song_dict.get('tempo'),
            key=song_dict.get('key'),
            camelot=song_dict.get('camelot'),
            genre=song_dict.get('genre', '')
        )

    playlist_objects = [dict_to_songinfo(s) for s in optimized_list]
    new_song_obj = dict_to_songinfo(new_song)

    best_position = 0
    min_added_distance = float('inf')

    for i in range(len(optimized_list) + 1):
        if i == 0:
            added_distance = distance(new_song_obj, playlist_objects[0])
        elif i == len(optimized_list):
            added_distance = distance(playlist_objects[-1], new_song_obj)
        else:
            old_distance = distance(playlist_objects[i-1], playlist_objects[i])
            new_distance = (distance(playlist_objects[i-1], new_song_obj) +
                            distance(new_song_obj, playlist_objects[i]))
            added_distance = new_distance - old_distance

        if added_distance < min_added_distance:
            min_added_distance = added_distance
            best_position = i

    return optimized_list[:best_position] + [new_song] + optimized_list[best_position:]


@app.route('/songs', methods=['GET'])
def get_songs():
    return jsonify({'songs': master_song_list})


@app.route('/songs/<int:index>', methods=['DELETE'])
def delete_song(index):
    try:
        if 0 <= index < len(master_song_list):
            deleted_song = master_song_list.pop(index)
            return jsonify({'success': True, 'deleted': deleted_song, 'songs': master_song_list})
        else:
            return jsonify({'success': False, 'error': 'Index out of range'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)