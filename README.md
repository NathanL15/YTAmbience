# 🎥 Ambient YouTube Video Player

A local web application that transforms YouTube videos into ambient experiences by processing the audio with custom acoustic effects while keeping the video synchronized.

## ✨ Features

- **Real-time Audio Processing**: Download and process YouTube audio with ambient effects
- **Multiple Presets**: 
  - 🏠 **Small Room**: Intimate ambient effect with mild filtering
  - 🏛️ **Concert Hall**: Spacious sound with long reverb
  - 🚪 **Next Room**: Heavily muffled effect as if hearing from another room
- **Live Audio Switching**: Toggle between ambient and original YouTube audio
- **Synchronized Playback**: Video and processed audio stay in sync
- **Responsive Design**: Works on desktop and mobile devices
- **No Downloads**: Everything processed locally, no permanent files saved

## 🚀 Quick Start

### Prerequisites

1. **Python 3.7+** installed
2. **FFmpeg** installed and available in PATH
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Or use `winget install FFmpeg`

### Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Open your browser** and go to: `http://127.0.0.1:5000`

## 🎵 How It Works

### Audio Processing Pipeline

1. **Extract** video ID from YouTube URL
2. **Download** best available audio using yt-dlp
3. **Apply** ambient processing:
   - Low-pass filtering (reduces brightness)
   - Gain reduction (softens volume)
   - Reverb effects (adds spaciousness)
   - Stereo widening (enhances spatial feel)
4. **Serve** processed audio alongside muted YouTube video

### Ambient Presets

| Preset | Low-Pass Filter | Reverb Decay | Gain Reduction | Special Effects |
|--------|----------------|--------------|----------------|-----------------|
| **Small Room** | 5000 Hz | 0.5s | -6 dB | Mild stereo widening |
| **Concert Hall** | 3500 Hz | 2.5s | -10 dB | Enhanced stereo spread |
| **Next Room** | 2500 Hz | 1.2s | -12 dB | Extra muffling at 2kHz |

## 🎮 Usage

1. **Paste YouTube URL** in the input field
2. **Select ambient preset** from dropdown
3. **Click "Create Ambient Experience"**
4. **Wait** for processing (usually 30-60 seconds)
5. **Enjoy** your ambient video with custom controls:
   - Switch between Ambient/Original audio
   - Change presets on-the-fly
   - Video continues playing throughout

## 🛠️ Technical Details

### Architecture
- **Backend**: Flask (Python)
- **Audio Processing**: pydub, scipy, numpy
- **YouTube Integration**: yt-dlp
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Audio Codec**: MP3 (192kbps)

### File Structure
```
ambient-youtube/
├── app.py                 # Flask backend with processing pipeline
├── requirements.txt       # Python dependencies
├── templates/
│   ├── index.html        # Home page with URL input
│   └── player.html       # Video player with ambient controls
└── static/
    └── processed/        # Temporary processed audio files
```

### Dependencies
- `Flask` - Web framework
- `yt-dlp` - YouTube audio downloading
- `pydub` - Audio manipulation and effects
- `numpy` - Numerical processing for audio
- `scipy` - Advanced audio processing (reverb)

## 🔧 Customization

### Adding New Presets

Edit the `PRESETS` dictionary in `app.py`:

```python
PRESETS = {
    'your_preset': {
        'name': 'Your Preset Name',
        'low_pass_cutoff': 4000,    # Hz
        'reverb_decay': 1.0,        # seconds
        'gain_reduction': -8,       # dB
        'stereo_width': 1.3,        # multiplier
        'extra_muffling': False     # boolean
    }
}
```

### Adjusting Audio Quality

Modify the `ydl_opts` in the `download_audio()` function:

```python
ydl_opts = {
    'format': 'bestaudio/best',
    'audioquality': '320K',  # Higher quality
    # ... other options
}
```

## ⚠️ Limitations

- **Processing Time**: 30-60 seconds per video depending on length
- **Storage**: Temporary files created during processing
- **YouTube ToS**: Respect YouTube's terms of service
- **Browser Autoplay**: Some browsers block autoplay, requiring user interaction

## 🐛 Troubleshooting

### Common Issues

**"FFmpeg not found"**
- Ensure FFmpeg is installed and in your system PATH
- Test with `ffmpeg -version` in terminal

**"Failed to download audio"**
- Check if YouTube URL is valid and accessible
- Some videos may be region-blocked or have restrictions

**Audio not playing**
- Browser may block autoplay - click play button manually
- Check browser console for JavaScript errors

**Processing takes too long**
- Longer videos take more time to process
- Check internet connection for download speed

## 📝 License

This project is for educational purposes. Respect YouTube's Terms of Service and copyright laws.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 🎯 Future Enhancements

- [ ] Real-time audio visualization
- [ ] Custom EQ controls
- [ ] Playlist support
- [ ] Audio export options
- [ ] Advanced reverb with impulse responses
- [ ] User-created preset sharing
