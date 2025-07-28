from services.task_manager import TaskManager
from services.chord_detector import ChordDetector
import librosa
import numpy
import json
import os
from datetime import datetime

class AudioProcessor:
    def __init__(self):
        self.task_manager = TaskManager()
        self.chord_detector = ChordDetector()

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

            # extract chords
            chord_data = self.chord_detector.detect_chords(y, sr)
            results['chords'] = chord_data

            return results
        except Exception as e:
            pass