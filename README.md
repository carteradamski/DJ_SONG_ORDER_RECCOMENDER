# DJ Playlist Optimizer

I started learning to be a DJ. Realized it sounded better to mix songs that had similar BPMs and keys. Made this program to take the songs you want to listen to and then it gives an optimal order to play the songs to have seamless transitions.

## How It Works

This web application optimizes your Spotify playlists for smooth DJ transitions by:
- Analyzing tempo (BPM) and musical key of each track
- Using the Camelot Wheel system for harmonic mixing
- Reordering songs to minimize jarring transitions
- Supporting export back to Spotify-compatible CSV format

## Features

- **CSV Upload**: Upload your Spotify playlist exported as CSV
- **Smart Optimization**: Automatically reorders songs for smooth BPM and key transitions
- **Camelot Wheel**: Uses harmonic mixing principles for key compatibility
- **CSV Download**: Export optimized playlist for re-import to Spotify

## Usage

1. Export your Spotify playlist as a CSV file
2. Upload the CSV file to the web app
3. Click "Optimize Playlist" to reorder songs
4. Download the optimized CSV
5. Import back to Spotify

## Installation

```bash
pip install -r requirements.txt
python app.py
```

Then open your browser to `http://localhost:5000`

## Technical Details

The optimization algorithm uses:
- **Tempo matching**: Considers BPM and harmonic BPM ratios (2:1, 1:2)
- **Key distance**: Uses Camelot Wheel notation for harmonic compatibility
- **TSP-based optimization**: Traveling salesman problem approach for minimal transitions
- **2-opt improvement**: Local optimization for better results
