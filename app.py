"""
DJ Playlist Optimizer - Flask Web App
CSV Upload and Download for Spotify Playlist Import
"""

from flask import Flask, render_template, request, jsonify, send_file
import csv
import io

app = Flask(__name__)

# In-memory storage for song list
song_list = []

# Spotify Key mapping (pitch class notation to key names)
KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Camelot wheel lookup: (key_name, scale) -> camelot notation
CAMELOT_WHEEL = {
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


class SongInfo:
    """Container for song data"""
    def __init__(self, title, artist, tempo=None, key=None, camelot=None, genre=''):
        self.title = title
        self.artist = artist
        self.tempo = tempo if tempo else None
        self.key = key if key else None
        self.camelot = camelot if camelot else None
        self.genre = genre if genre else ''

    def to_dict(self):
        return {
            'title': self.title,
            'artist': self.artist,
            'tempo': self.tempo,
            'key': self.key,
            'camelot': self.camelot,
            'genre': self.genre
        }


def convert_spotify_key_to_notation(key_num, mode):
    """Convert Spotify's Key (0-11) and Mode (0=minor, 1=major) to readable format and Camelot"""
    try:
        key_num = int(key_num)
        mode = int(mode)
        
        if key_num < 0 or key_num > 11:
            return None, None
        
        key_name = KEY_NAMES[key_num]
        scale = 'major' if mode == 1 else 'minor'
        
        key_display = f"{key_name} {scale}"
        camelot = CAMELOT_WHEEL.get((key_name, scale))
        
        return key_display, camelot
    except (ValueError, IndexError):
        return None, None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    """Upload and parse a CSV file with Spotify export format"""
    global song_list
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': 'Only .csv files are allowed'}), 400

    try:
        # Read CSV file
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        
        song_list = []
        for row in csv_reader:
            # Parse Spotify CSV format
            # Expected columns: Track Name, Artist Name(s), Tempo, Key, Mode, Genres, etc.
            title = row.get('Track Name', '').strip()
            artist = row.get('Artist Name(s)', '').strip()
            
            if not title or not artist:
                continue
            
            # Parse tempo (round to integer)
            tempo_str = row.get('Tempo', '').strip()
            try:
                tempo = int(float(tempo_str)) if tempo_str else None
            except (ValueError, TypeError):
                tempo = None
            
            # Parse key and mode from Spotify format
            key_num = row.get('Key', '').strip()
            mode = row.get('Mode', '').strip()
            
            if key_num and mode:
                key_display, camelot = convert_spotify_key_to_notation(key_num, mode)
            else:
                key_display = None
                camelot = None
            
            # Get genres
            genre = row.get('Genres', '').strip()
            
            song_dict = {
                'title': title,
                'artist': artist,
                'tempo': tempo,
                'key': key_display,
                'camelot': camelot,
                'genre': genre
            }
            song_list.append(song_dict)

        return jsonify({
            'success': True,
            'count': len(song_list),
            'songs': song_list
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download_csv', methods=['GET'])
def download_csv():
    """Download the current song list as CSV for Spotify import"""
    if not song_list:
        return jsonify({'success': False, 'error': 'No songs to download'}), 400

    # Create CSV in memory with Spotify-compatible format
    output = io.StringIO()
    fieldnames = ['title', 'artist', 'tempo', 'key', 'camelot', 'genre']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    
    writer.writeheader()
    for song in song_list:
        writer.writerow({
            'title': song.get('title', ''),
            'artist': song.get('artist', ''),
            'tempo': song.get('tempo', '') if song.get('tempo') else '',
            'key': song.get('key', '') if song.get('key') else '',
            'camelot': song.get('camelot', '') if song.get('camelot') else '',
            'genre': song.get('genre', '')
        })
    
    # Convert to bytes for download
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='optimized_playlist.csv'
    )


@app.route('/optimize', methods=['POST'])
def optimize_playlist():
    """Optimize the current playlist order and return the reordered list"""
    global song_list
    
    if not song_list:
        return jsonify({'success': False, 'error': 'No songs to optimize'}), 400
    
    try:
        song_list = make_End_list(song_list)
        return jsonify({
            'success': True,
            'count': len(song_list),
            'songs': song_list
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
    """Get the current song list"""
    return jsonify({'songs': song_list, 'count': len(song_list)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)