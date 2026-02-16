"""
DJ Playlist Optimizer - Song Data Fetcher

Setup Instructions:
1. Sign up for a free API key at: https://getsongbpm.com/api
2. Install required package: pip install requests
3. Replace 'YOUR_API_KEY_HERE' below with your actual API key
4. Run the script to test with example songs

Note: Free API tier has rate limits. Check getsongbpm.com for current limits.
"""

import requests


class SongInfo:
    """Container for song data"""
    def __init__(self, title, artist, bpm=None, key=None, camelot=None):
        self.title = title
        self.artist = artist
        self.bpm = bpm
        self.key = key  # Musical key (e.g., "C", "F#m")
        self.camelot = camelot  # Camelot notation (e.g., "8B", "9A")
    
    def __repr__(self):
        return f"SongInfo('{self.title}' by {self.artist}, {self.bpm} BPM, Key: {self.key})"
    
    def __str__(self):
        return f"{self.title} - {self.artist} | {self.bpm} BPM | {self.key} ({self.camelot})"


def get_song_bpm_and_key(song_name, artist_name, api_key):
    """
    Fetch BPM and key information for a song using GetSongBPM API.
    
    Args:
        song_name (str): Name of the song
        artist_name (str): Name of the artist
        api_key (str): Your GetSongBPM API key
    
    Returns:
        SongInfo: Object containing song data, or None if not found
    
    Example:
        >>> song = get_song_bpm_and_key("Levels", "Avicii", "your_api_key")
        >>> print(f"BPM: {song.bpm}, Key: {song.key}")
    """
    
    # API endpoint for searching songs
    search_url = "https://api.getsongbpm.com/search/"
    
    # Build search query
    search_params = {
        'api_key': api_key,
        'type': 'song',
        'lookup': f"{artist_name} {song_name}"
    }
    
    try:
        # Step 1: Search for the song
        print(f"Searching for: {song_name} by {artist_name}...")
        response = requests.get(search_url, params=search_params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we found results
        if 'search' not in data or len(data['search']) == 0:
            print(f"  ✗ No results found")
            return None
        
        # Get the first (most relevant) result
        first_result = data['search'][0]
        song_id = first_result.get('id')
        
        # Step 2: Get detailed info for this song
        detail_url = "https://api.getsongbpm.com/song/"
        detail_params = {
            'api_key': api_key,
            'id': song_id
        }
        
        detail_response = requests.get(detail_url, params=detail_params, timeout=10)
        detail_response.raise_for_status()
        
        song_data = detail_response.json()
        
        if 'song' not in song_data:
            print(f"  ✗ Could not retrieve song details")
            return None
        
        # Extract the data
        song = song_data['song']
        artist = song.get('artist', {})
        
        result = SongInfo(
            title=song.get('title', song_name),
            artist=artist.get('name', artist_name),
            bpm=int(song.get('tempo')) if song.get('tempo') else None,
            key=song.get('key_of'),  # e.g., "Em", "C#"
            camelot=song.get('open_key')  # e.g., "9A", "8B"
        )
        
        print(f"  ✓ Found: {result}")
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"  ✗ API request failed: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


# ============================================================================
# CONFIGURATION
# ============================================================================

# TODO: Add your API key here (get one at https://getsongbpm.com/api)
API_KEY = 'YOUR_API_KEY_HERE'


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DJ Song BPM & Key Analyzer")
    print("=" * 70)
    print()
    
    # Check if API key is configured
    if API_KEY == 'YOUR_API_KEY_HERE':
        print("⚠️  WARNING: Please add your API key to the API_KEY variable above")
        print("   Sign up at: https://getsongbpm.com/api")
        print()
    
    # Example songs to test
    test_songs = [
        ("Levels", "Avicii"),
        ("One More Time", "Daft Punk"),
        ("Strobe", "Deadmau5"),
    ]
    
    results = []
    
    for song_name, artist_name in test_songs:
        song_info = get_song_bpm_and_key(song_name, artist_name, API_KEY)
        if song_info:
            results.append(song_info)
        print()
    
    # Display summary
    if results:
        print("=" * 70)
        print("FOUND SONGS:")
        print("=" * 70)
        for song in results:
            print(f"  • {song}")