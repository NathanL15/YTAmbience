from flask import Flask, request, render_template, jsonify, url_for, send_from_directory
import yt_dlp
from pydub import AudioSegment
from pydub.effects import low_pass_filter, normalize
import uuid
import os
import re
import tempfile
import numpy as np
from scipy import signal
import subprocess
import shutil

app = Flask(__name__)

# Create processed directory if it doesn't exist
os.makedirs('static/processed', exist_ok=True)

# Ambience presets configuration
PRESETS = {
    'small_room': {
        'name': 'Small Room',
        'low_pass_cutoff': 3000,
        'reverb_decay': 1.5,
        'gain_reduction': -12,
        'stereo_width': 1.8,
        'distance_factor': 0.4
    },
    'concert_hall': {
        'name': 'Concert Hall',
        'low_pass_cutoff': 2000,
        'reverb_decay': 4.0,
        'gain_reduction': -18,
        'stereo_width': 2.2,
        'distance_factor': 0.2
    },
    'next_room': {
        'name': 'Next Room',
        'low_pass_cutoff': 1500,
        'reverb_decay': 2.8,
        'gain_reduction': -20,
        'stereo_width': 1.6,
        'extra_muffling': True,
        'distance_factor': 0.15
    }
}

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def check_ffmpeg():
    """Check if FFmpeg is available"""
    return shutil.which('ffmpeg') is not None

def download_audio(video_id):
    """Download audio from YouTube using yt-dlp"""
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, f"{video_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_file,
        'noplaylist': True,
        # Try to download without post-processing first
        'postprocessors': []
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
        
        # Find the downloaded file
        downloaded_file = None
        for file in os.listdir(temp_dir):
            if file.startswith(video_id):
                downloaded_file = os.path.join(temp_dir, file)
                break
        
        if not downloaded_file:
            raise Exception("Downloaded file not found")

        # Load and normalize the audio
        audio = AudioSegment.from_file(downloaded_file)
        normalized_audio = normalize_audio(audio)
        normalized_audio.export(downloaded_file, format="mp3")

        return downloaded_file
    
    except FileNotFoundError as e:
        if "ffmpeg" in str(e).lower() or "avconv" in str(e).lower():
            raise Exception("FFmpeg is not installed. Please install FFmpeg and add it to your system PATH, or try using a different audio format.")
        else:
            raise Exception(f"File not found: {str(e)}")
    except yt_dlp.utils.DownloadError as e:
        raise Exception(f"Failed to download video: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        if "ffmpeg" in error_msg.lower() or "avconv" in error_msg.lower():
            raise Exception("FFmpeg is not installed. Please install FFmpeg and add it to your system PATH.")
        elif "[WinError 2]" in error_msg:
            raise Exception("FFmpeg is required but not found. Please install FFmpeg and add it to your system PATH.")
        else:
            raise Exception(f"Failed to download audio: {error_msg}")

def apply_reverb(audio_segment, decay_time):
    """Apply enhanced reverb effect using multiple delays for more spacious sound"""
    # Convert to numpy array
    samples = audio_segment.get_array_of_samples()
    if audio_segment.channels == 2:
        samples = np.array(samples).reshape((-1, 2))
    else:
        samples = np.array(samples)
    
    # Create reverb using multiple delayed versions with different characteristics
    sample_rate = audio_segment.frame_rate
    
    reverb_audio = samples.astype(np.float32)
    
    # Multiple delay lines for more complex reverb
    delay_times = [0.03, 0.07, 0.13, 0.21, 0.34]  # Various delay times in seconds
    
    for delay_time in delay_times:
        delay_samples = int(delay_time * sample_rate)
        
        # Add multiple echoes with decreasing amplitude for each delay line
        num_echoes = max(3, int(decay_time * 8))  # More echoes for longer decay
        for i in range(1, num_echoes + 1):
            delay = delay_samples * i
            # Much more conservative amplitude to prevent clipping
            amplitude = 0.2 * (0.5 ** i) * (1.0 / len(delay_times))
            
            if audio_segment.channels == 2:
                delayed = np.zeros_like(reverb_audio)
                if delay < len(samples):
                    delayed[delay:] = samples[:-delay] * amplitude
                reverb_audio += delayed
            else:
                delayed = np.zeros_like(reverb_audio)
                if delay < len(samples):
                    delayed[delay:] = samples[:-delay] * amplitude
                reverb_audio += delayed
    
    # Convert back to AudioSegment
    reverb_audio = np.clip(reverb_audio, -32768, 32767).astype(np.int16)
    
    if audio_segment.channels == 2:
        reverb_audio = reverb_audio.flatten()
    
    return AudioSegment(
        reverb_audio.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=audio_segment.channels
    )

def apply_stereo_widening(audio_segment, width_factor):
    """Apply stereo widening effect"""
    if audio_segment.channels != 2:
        return audio_segment
    
    # Convert to numpy array
    samples = np.array(audio_segment.get_array_of_samples()).reshape((-1, 2))
    left = samples[:, 0].astype(np.float32)
    right = samples[:, 1].astype(np.float32)
    
    # Calculate mid and side signals
    mid = (left + right) / 2
    side = (left - right) / 2
    
    # Widen by increasing side signal
    side *= width_factor
    
    # Convert back to left/right
    new_left = mid + side
    new_right = mid - side
    
    # Combine and normalize
    new_samples = np.column_stack((new_left, new_right))
    new_samples = np.clip(new_samples, -32768, 32767).astype(np.int16)
    
    return AudioSegment(
        new_samples.flatten().tobytes(),
        frame_rate=audio_segment.frame_rate,
        sample_width=2,
        channels=2
    )

def process_audio(audio_file_path, preset_name):
    """Apply ambience processing based on preset"""
    preset = PRESETS[preset_name]
    
    # Load audio
    audio = AudioSegment.from_file(audio_file_path)
    
    # Convert to stereo if mono
    if audio.channels == 1:
        audio = audio.set_channels(2)
    
    # Apply much more aggressive initial gain reduction to prevent clipping
    audio = audio + preset['gain_reduction'] - 10  # Extra -10dB reduction
    
    # Apply distance simulation - reduce volume significantly to simulate being far away
    distance_reduction = -25 * (1 - preset['distance_factor'])  # Even more reduction
    audio = audio + distance_reduction
    
    # Apply low-pass filter (more aggressive for distance)
    audio = low_pass_filter(audio, preset['low_pass_cutoff'])
    
    # Apply extra muffling for "Next Room" preset
    if preset.get('extra_muffling'):
        # Additional EQ dip around 2kHz for more muffled sound
        muffled_audio = low_pass_filter(audio, 1000).apply_gain(-8)  # Even more aggressive muffling
        audio = audio.overlay(muffled_audio, gain_during_overlay=-8)
        # Apply additional high-frequency roll-off
        audio = low_pass_filter(audio, 800)
    
    # Apply reverb (much more pronounced)
    audio = apply_reverb(audio, preset['reverb_decay'])
    
    # Apply stereo widening for spatial effect
    audio = apply_stereo_widening(audio, preset['stereo_width'])
    
    # Apply additional gain reduction before normalization to prevent clipping
    audio = audio - 5  # Extra safety margin
    
    # Final normalization to prevent clipping but keep it very quiet
    audio = normalize(audio)
    
    return audio

def normalize_audio(audio_segment):
    """Normalize audio to a target dBFS level."""
    target_dBFS = -40.0  # Very quiet target loudness level to prevent distortion
    change_in_dBFS = target_dBFS - audio_segment.dBFS
    return audio_segment.apply_gain(change_in_dBFS)

@app.route('/')
def index():
    """Home page with URL input form"""
    return render_template('index.html', presets=PRESETS)

@app.route('/process', methods=['POST'])
def process_video():
    """Process YouTube video and return playback page"""
    youtube_url = request.form.get('youtube_url')
    preset = request.form.get('preset', 'small_room')
    
    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    # Check if FFmpeg is available
    if not check_ffmpeg():
        return jsonify({
            'error': 'FFmpeg is required but not installed. Please install FFmpeg and add it to your system PATH. Visit https://ffmpeg.org/download.html for installation instructions.'
        }), 500
    
    # Extract video ID
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    try:
        # Download audio
        audio_file = download_audio(video_id)
        
        # Process audio with ambience
        processed_audio = process_audio(audio_file, preset)
        
        # Save processed audio
        output_filename = f"{uuid.uuid4().hex}.mp3"
        output_path = os.path.join('static', 'processed', output_filename)
        processed_audio.export(output_path, format='mp3')
        
        # Clean up temporary file
        os.remove(audio_file)
        os.rmdir(os.path.dirname(audio_file))
        
        # Return playback page
        return render_template('player.html', 
                             video_id=video_id,
                             audio_file=output_filename,
                             preset=preset,
                             preset_name=PRESETS[preset]['name'],
                             presets=PRESETS)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reprocess', methods=['POST'])
def reprocess_audio():
    """Reprocess audio with new preset"""
    video_id = request.form.get('video_id')
    new_preset = request.form.get('preset')
    
    if not video_id or not new_preset:
        return jsonify({'error': 'Video ID and preset are required'}), 400
    
    # Check if FFmpeg is available
    if not check_ffmpeg():
        return jsonify({
            'error': 'FFmpeg is required but not installed. Please install FFmpeg and add it to your system PATH.'
        }), 500
    
    try:
        # Download audio again
        audio_file = download_audio(video_id)
        
        # Process with new preset
        processed_audio = process_audio(audio_file, new_preset)
        
        # Save new processed audio
        output_filename = f"{uuid.uuid4().hex}.mp3"
        output_path = os.path.join('static', 'processed', output_filename)
        processed_audio.export(output_path, format='mp3')
        
        # Clean up temporary file
        os.remove(audio_file)
        os.rmdir(os.path.dirname(audio_file))
        
        return jsonify({
            'audio_file': output_filename,
            'preset_name': PRESETS[new_preset]['name']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/processed/<filename>')
def serve_processed_audio(filename):
    """Serve processed audio files"""
    return send_from_directory('static/processed', filename)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
