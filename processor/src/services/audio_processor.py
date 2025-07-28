from services.task_manager import TaskManager
from services.chord_detector import ChordDetector
from services.lyric_extractor import LyricExtractor
import librosa
from flask import current_app
import json
import os
from datetime import datetime

class AudioProcessor:
    def __init__(self):
        self.task_manager = TaskManager()
        self.chord_detector = ChordDetector()
        self.lyric_extractor = LyricExtractor();

    def process_audio(self, job_id):
        try:
            results = {
                'job_id': job_id,
                'processing_started': datetime.now().isoformat(),
                'status': 'processing'
            }

            job_data = self.task_manager.get_job(job_id)
            filepath = job_data['filepath']

            # load audio with librosa
            print(f"Loading audio file: {filepath}")
            try:
                y, sr = librosa.load(filepath, sr=22050)   # 22050 is common sr in audio processing, good for chord detection

                if len(y) == 0:
                    raise ValueError('Audio file is empty or corrupted')
                
                duration = librosa.get_duration(y=y, sr=sr)

                if duration < 1.0:
                    raise ValueError('Audio file is too short (Minimum 1 second)')
                
                print(f"Audio file loaded successfully: {duration:.2f} seconds, {sr} Hz")
            
            except Exception as audio_error:
                print(f"Error loading audio file: {str(audio_error)}")
                results['status'] = 'failed'
                results['error'] = str(audio_error)
                return results
            
            # set basic metadata
            results['metadata'] = {
                'duration': duration,
                'sample_rate': sr
            }

            print("Extracting chords...")
            # extract chords
            chord_data = self.chord_detector.detect_chords(y, sr)
            results['chords'] = chord_data

            # extract lyrics
            print("Extracting lyrics...")
            lyrics_data = self.lyric_extractor.extract_lyrics(filepath)
            results['lyrics'] = lyrics_data


            results['status'] = 'completed'
            results['processing_completed'] = datetime.now().isoformat()
            # Calculate processing time
            start_time = datetime.fromisoformat(results['processing_started'])
            end_time = datetime.fromisoformat(results['processing_completed'])
            results['processing_time'] = (end_time - start_time).total_seconds()

            # save results
            results_file = os.path.join(current_app.config['OUTPUT_FOLDER'], f"{job_id}_results.json")
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=4)

            
            print(f"Processing completed for job {job_id}")
            return results
        except Exception as e:
            error_msg = str(e)
            print(f"Error processing audio: {error_msg}")
            
            # Provide more specific error messages for common issues
            if "ffmpeg" in error_msg.lower():
                detailed_error = ("FFmpeg not found. Please install FFmpeg for audio format support. "
                               "See FFMPEG_SETUP.md for installation instructions.")
            elif "could not open" in error_msg.lower() or "invalid" in error_msg.lower():
                detailed_error = ("Invalid or corrupted audio file. Please ensure the file is a valid MP3 "
                               "and not corrupted. Try with a different audio file.")
            elif "format not supported" in error_msg.lower():
                detailed_error = ("Audio format not supported. Please use MP3, WAV, or other common audio formats.")
            else:
                detailed_error = f"Audio processing failed: {error_msg}"
            
            results['status'] = 'failed'
            results['error'] = detailed_error
            results['processing_completed'] = datetime.utcnow().isoformat()
            return results