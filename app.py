"""
DJ Playlist Optimizer - Flask Web App
Powered by GetSongBPM.com
"""

from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)
API_KEY = '6770b0b81d2bd417dba76b33fd591683'

# In-memory storage for master song list
master_song_list = []


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


def get_song_bpm_and_key(song_name, artist_name):
    """Fetch BPM and key from GetSongBPM API"""
    search_url = "https://api.getsong.co/search/"
    
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
        detail_url = "https://api.getsong.co/song/"
        detail_params = {'api_key': API_KEY, 'id': song_id}
        
        detail_response = requests.get(detail_url, params=detail_params, timeout=10)
        detail_response.raise_for_status()
        song_data = detail_response.json()
        
        if 'song' not in song_data:
            return None
        
        song = song_data['song']
        artist = song.get('artist', {})
        
        # Extract genre from artist.genres array (API returns array of genres)
        genres = artist.get('genres', [])
        genre = ', '.join(genres) if genres else ''
        
        return SongInfo(
            title=song.get('title', song_name),
            artist=artist.get('name', artist_name),
            tempo=int(song.get('tempo')) if song.get('tempo') else None,
            key=song.get('key_of'),
            camelot=song.get('open_key'),
            genre=genre
        )
        
    except Exception as e:
        print(f"Error: {e}")
        return None


@app.route('/')
def index():
    """Main page"""
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
                
                # Add to master list if not already there
                if not any(s['title'] == song_dict['title'] and s['artist'] == song_dict['artist'] for s in master_song_list):
                    master_song_list.append(song_dict)
                results.append(song_dict)
            # If song not found in API, skip it (don't add to master list)
    
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
        # Read and parse the file
        content = file.read().decode('utf-8')
        lines = content.strip().split('\n')
        
        songs_to_add = []
        for line in lines:
            line = line.strip()
            if not line or '|' not in line:
                continue  # Skip empty lines or lines without delimiter
            
            parts = line.split('|')
            if len(parts) >= 2:
                title = parts[0].strip()
                artist = parts[1].strip()
                if title and artist:
                    songs_to_add.append({'title': title, 'artist': artist})
        
        # Process each song (fetch BPM/key data)
        results = []
        skipped = []
        for song_data in songs_to_add:
            song_name = song_data['title']
            artist_name = song_data['artist']
            
            song_info = get_song_bpm_and_key(song_name, artist_name)
            if song_info:
                song_dict = song_info.to_dict()
                
                # Add to master list if not already there
                if not any(s['title'] == song_dict['title'] and s['artist'] == song_dict['artist'] for s in master_song_list):
                    master_song_list.append(song_dict)
                results.append(song_dict)
            else:
                # Song not found in API, skip it
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
    """
    Calculate harmonic distance between two Camelot keys.
    Returns 0 for identical keys, 1 for compatible mixes, higher for incompatible.
    """
    if not camelot1 or not camelot2:
        return 6  # Maximum penalty for missing key data
    
    # Parse Camelot notation (e.g., "8A" -> number=8, letter='A')
    try:
        num1 = int(''.join(filter(str.isdigit, camelot1)))
        letter1 = ''.join(filter(str.isalpha, camelot1)).upper()
        num2 = int(''.join(filter(str.isdigit, camelot2)))
        letter2 = ''.join(filter(str.isalpha, camelot2)).upper()
    except:
        return 6  # Invalid format
    
    # Same key = perfect match
    if num1 == num2 and letter1 == letter2:
        return 0
    
    # Same number, different letter (relative major/minor) = compatible
    if num1 == num2:
        return 1
    
    # Calculate minimum distance around the wheel (1-12 wraps)
    wheel_distance = min(abs(num1 - num2), 12 - abs(num1 - num2))
    
    # Adjacent number with same letter = compatible
    if wheel_distance == 1 and letter1 == letter2:
        return 1
    
    # Combined: wheel distance + letter mismatch penalty
    letter_penalty = 0 if letter1 == letter2 else 1
    return wheel_distance + letter_penalty

def distance(SONG1, SONG2):
    tempo_diff1 = abs(SONG1.tempo - SONG2.tempo) if SONG1.tempo and SONG2.tempo else 100
    tempo_diff2 = abs(SONG1.tempo - 2 * SONG2.tempo) if SONG1.tempo and SONG2.tempo else 100 
    tempo_diff3 = abs(2 * SONG1.tempo - SONG2.tempo) if SONG1.tempo and SONG2.tempo else 100
    return min(tempo_diff1, tempo_diff2, tempo_diff3) +  4.0 * abs(key_distance(SONG1.camelot, SONG2.camelot))
    

def make_End_list(Song_List):
    """
    Generate optimized playlist using TSP with nearest neighbor + 2-opt.
    Returns list of songs in optimal playing order.
    """
    if not Song_List or len(Song_List) <= 1:
        return Song_List
    
    # Convert dicts to SongInfo objects for distance calculation
    def dict_to_songinfo(song_dict):
        s = SongInfo(
            title=song_dict.get('title', ''),
            artist=song_dict.get('artist', ''),
            tempo=song_dict.get('tempo'),
            key=song_dict.get('key'),
            camelot=song_dict.get('camelot')
        )
        s.genre = song_dict.get('genre', '')
        return s
    
    song_objects = [dict_to_songinfo(s) for s in Song_List]
    
    # Nearest neighbor algorithm starting from first song (random start)
    unvisited = set(range(len(song_objects)))
    current = 0  # Start from first song
    tour = [current]
    unvisited.remove(current)
    
    while unvisited:
        nearest = min(unvisited, key=lambda i: distance(song_objects[current], song_objects[i]))
        tour.append(nearest)
        unvisited.remove(nearest)
        current = nearest
    
    # 2-opt improvement: swap edges to reduce total distance
    improved = True
    while improved:
        improved = False
        for i in range(1, len(tour) - 2):
            for j in range(i + 1, len(tour)):
                if j - i == 1:
                    continue
                
                # Calculate current distance of two edges
                current_dist = (distance(song_objects[tour[i-1]], song_objects[tour[i]]) +
                               distance(song_objects[tour[j-1]], song_objects[tour[j % len(tour)]]))
                
                # Calculate distance if we reverse the segment between i and j
                new_dist = (distance(song_objects[tour[i-1]], song_objects[tour[j-1]]) +
                           distance(song_objects[tour[i]], song_objects[tour[j % len(tour)]]))
                
                if new_dist < current_dist:
                    # Reverse the segment
                    tour[i:j] = reversed(tour[i:j])
                    improved = True
                    break
            if improved:
                break
    
    # Return songs in optimized order
    return [Song_List[i] for i in tour]


def add_song_after(optimized_list, new_song):
    """
    Add a new song to an already optimized playlist at the position that adds the least distance.
    Returns the updated playlist with the song inserted optimally.
    """
    if not optimized_list:
        return [new_song]
    
    if len(optimized_list) == 1:
        return optimized_list + [new_song]
    
    # Convert to SongInfo objects for distance calculation
    def dict_to_songinfo(song_dict):
        s = SongInfo(
            title=song_dict.get('title', ''),
            artist=song_dict.get('artist', ''),
            tempo=song_dict.get('tempo'),
            key=song_dict.get('key'),
            camelot=song_dict.get('camelot')
        )
        s.genre = song_dict.get('genre', '')
        return s
    
    playlist_objects = [dict_to_songinfo(s) for s in optimized_list]
    new_song_obj = dict_to_songinfo(new_song)
    
    best_position = 0
    min_added_distance = float('inf')
    
    # Try inserting at each position (including at the end)
    for i in range(len(optimized_list) + 1):
        if i == 0:
            # Insert at beginning
            added_distance = distance(new_song_obj, playlist_objects[0])
        elif i == len(optimized_list):
            # Insert at end
            added_distance = distance(playlist_objects[-1], new_song_obj)
        else:
            # Insert between position i-1 and i
            # Remove old edge, add two new edges
            old_distance = distance(playlist_objects[i-1], playlist_objects[i])
            new_distance = (distance(playlist_objects[i-1], new_song_obj) + 
                           distance(new_song_obj, playlist_objects[i]))
            added_distance = new_distance - old_distance
        
        if added_distance < min_added_distance:
            min_added_distance = added_distance
            best_position = i
    
    # Insert the song at the best position
    result = optimized_list[:best_position] + [new_song] + optimized_list[best_position:]
    return result


@app.route('/songs', methods=['GET'])
def get_songs():
    """Get all songs in the master list"""
    return jsonify({'songs': master_song_list})


@app.route('/songs/<int:index>', methods=['DELETE'])
def delete_song(index):
    """Delete a song from the master list by index"""
    try:
        if 0 <= index < len(master_song_list):
            deleted_song = master_song_list.pop(index)
            return jsonify({'success': True, 'deleted': deleted_song, 'songs': master_song_list})
        else:
            return jsonify({'success': False, 'error': 'Index out of range'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
def main():
    """Test the API with a sample song"""
    test_song = "Shape of You"
    test_artist = "Ed Sheeran"
    
    print(f"Testing API for: {test_artist} - {test_song}")
    result = get_song_bpm_and_key(test_song, test_artist)
    
    if result:
        print(f"  ✓ Found: {result.to_dict()}")
    else:
        print(f"  ✗ No data found")


if __name__ == '__main__':
    app.run(debug=True, port=5000)
    app.run(debug=True, port=5000)