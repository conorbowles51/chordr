import librosa
import numpy as np
from scipy.signal import find_peaks

class ChordDetector:
    def __init__(self):
        self.chord_templates = self._create_chord_templates()
        self.chord_names = [
            'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
            'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'A#m', 'Bm'
        ]

    def detect_chords(self, y, sr, hop_length=512):
        try:
            # extract chromagram from amplitude
            # all the data is actually in the amplitude! stft (fourier transform)
            # unmixes it into frequencies. Crazy!
            chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop_length)

            # extract tempo
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)

            # estimates key with Krumhansl-Schmuckler. Do not understand this one
            key = self._estimate_key(chroma)

            # extract chords
            chord_progression = self._detect_chord_progression(chroma, sr, hop_length)

            # Smooth chord progression to remove rapid changes
            smoothed_progression = self._smooth_chord_progression(chord_progression)
            
            results = {
                'progression': smoothed_progression,
                'key': key,
                'tempo': float(tempo) if not np.isnan(tempo) and not np.isinf(tempo) else 120.0,
                'confidence': self._calculate_confidence(chroma),
                'total_chords': len(smoothed_progression),
                'unique_chords': len(set([c['chord'] for c in smoothed_progression]))
            }
            
            print(f"Detected {len(smoothed_progression)} chord changes")
            tempo_value = float(tempo) if not np.isnan(tempo) and not np.isinf(tempo) else 120.0
            print(f"Key: {key}, Tempo: {tempo_value:.1f} BPM")
            
            return results
        except Exception as e:
            print(f"Error in chord detection: {str(e)}")
            return {
                'progression': [],
                'key': 'Unknown',
                'tempo': 120.0,
                'confidence': 0.0,
                'error': str(e)
            }

    def _create_chord_templates(self):
        templates = {}

        # root, maj3, 5th
        major_intervals = [0, 4, 7]
        # root, min3, 5th
        minor_intervals = [0, 3, 7]

        # create a template for each root note
        for root in range(12):
            # Major chord
            major_template = np.zeros(12)
            for interval in major_intervals:
                major_template[(root + interval) % 12] = 1
            templates[f'{root}_major'] = major_template
            
            # Minor chord
            minor_template = np.zeros(12)
            for interval in minor_intervals:
                minor_template[(root + interval) % 12] = 1
            templates[f'{root}_minor'] = minor_template
        
        return templates
    
    def _estimate_key(self, chroma):
        # estimate the key of the song using Krumhansl-Schmuckler algorithm
        # krumhansl-Schmuckler key profiles
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        # Average chroma over time
        mean_chroma = np.mean(chroma, axis=1)
        
        # Check for valid chroma
        if np.sum(mean_chroma) == 0 or np.any(np.isnan(mean_chroma)):
            return 'Unknown'
        
        # Normalize safely
        mean_chroma = mean_chroma / (np.sum(mean_chroma) + 1e-8)  # Add small number to avoid division by zero
        
        best_correlation = -1
        best_key = 'C major'
        
        # Test all major keys
        for i in range(12):
            rotated_profile = np.roll(major_profile, i)
            try:
                correlation = np.corrcoef(mean_chroma, rotated_profile)[0, 1]
                if not np.isnan(correlation) and not np.isinf(correlation) and correlation > best_correlation:
                    best_correlation = correlation
                    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    best_key = f"{note_names[i]} major"
            except:
                continue
        
        # Test all minor keys
        for i in range(12):
            rotated_profile = np.roll(minor_profile, i)
            try:
                correlation = np.corrcoef(mean_chroma, rotated_profile)[0, 1]
                if not np.isnan(correlation) and not np.isinf(correlation) and correlation > best_correlation:
                    best_correlation = correlation
                    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    best_key = f"{note_names[i]} minor"
            except:
                continue
        
        return best_key
    
    def _detect_chord_progression(self, chroma, sr, hop_length):
        progression = []
        
        # segment the audio into chord-length chunks
        segment_length = int(2 * sr / hop_length)  # 2 seconds
        
        for i in range(0, chroma.shape[1], segment_length):
            end_idx = min(i + segment_length, chroma.shape[1])
            segment_chroma = np.mean(chroma[:, i:end_idx], axis=1)
            
            # Normalize
            if np.sum(segment_chroma) > 0:
                segment_chroma = segment_chroma / np.sum(segment_chroma)
            
            # Match against chord templates
            best_chord, confidence = self._match_chord_template(segment_chroma)
            
            # Calculate time
            time_seconds = librosa.frames_to_time(i, sr=sr, hop_length=hop_length)
            
            progression.append({
                'time': float(time_seconds) if not np.isnan(time_seconds) and not np.isinf(time_seconds) else 0.0,
                'chord': best_chord,
                'confidence': float(confidence) if not np.isnan(confidence) and not np.isinf(confidence) else 0.0
            })

        return progression
    
    def _match_chord_template(self, chroma_vector):
        best_correlation = -1
        best_chord = 'N'  # No chord
        
        # Check for valid chroma vector
        if np.sum(chroma_vector) == 0 or np.any(np.isnan(chroma_vector)):
            return best_chord, 0.0
        
        for template_name, template in self.chord_templates.items():
            # Use safer correlation calculation
            try:
                correlation = np.corrcoef(chroma_vector, template)[0, 1]
                if np.isnan(correlation) or np.isinf(correlation):
                    correlation = 0
            except:
                correlation = 0
            
            if correlation > best_correlation:
                best_correlation = correlation
                root, chord_type = template_name.split('_')
                chord_name = self._get_chord_name(int(root), chord_type)
                best_chord = chord_name
        
        # If correlation is too low, consider it as no chord
        if best_correlation < 0.6:
            best_chord = 'N'
            best_correlation = 0
        
        return best_chord, best_correlation
    

    def _get_chord_name(self, root, chord_type):
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        base_name = note_names[root]
        
        if chord_type == 'minor':
            return base_name + 'm'
        else:
            return base_name

    def _smooth_chord_progression(self, progression, min_duration=1.0):
        if len(progression) <= 1:
            return progression
        
        smoothed = [progression[0]]
        
        for i in range(1, len(progression)):
            current_chord = progression[i]
            last_chord = smoothed[-1]
            
            # If this chord is different from the last and the duration is too short, skip it
            duration = current_chord['time'] - last_chord['time']
            
            if (current_chord['chord'] != last_chord['chord'] and 
                duration >= min_duration) or i == len(progression) - 1:
                smoothed.append(current_chord)
        
        return smoothed
    
    def _calculate_confidence(self, chroma):
        """Calculate overall confidence of chord detection"""
        try:
            # Simple confidence based on chroma clarity
            clarity = np.mean(np.max(chroma, axis=0) - np.mean(chroma, axis=0))
            confidence = min(clarity * 2, 1.0)  # Scale and cap at 1.0
            return float(confidence) if not np.isnan(confidence) and not np.isinf(confidence) else 0.5
        except:
            return 0.5  # Default confidence if calculation fails