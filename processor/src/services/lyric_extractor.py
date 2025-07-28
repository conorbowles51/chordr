import whisper
import os
import tempfile
from pydub import AudioSegment
import json

class LyricExtractor:
    """Service for extracting lyrics from audio using speech recognition"""
    
    def __init__(self, model_size='small'):
        """
        Initialize the lyric extractor
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                       'small' is better for music transcription than 'base'
        """
        self.model_size = model_size
        self.model = None
        # Don't load model during init - load it lazily when needed
    
    def _load_model(self):
        """Load the Whisper model lazily with fallback options"""
        if self.model is None:
            try:
                print(f"Loading Whisper model: {self.model_size}")
                self.model = whisper.load_model(self.model_size)
                print("Whisper model loaded successfully")
            except Exception as e:
                print(f"Error loading Whisper model {self.model_size}: {str(e)}")
                # Try fallback to base model if requested model fails
                if self.model_size != 'base':
                    try:
                        print("Falling back to base model...")
                        self.model = whisper.load_model('base')
                        self.model_size = 'base'
                        print("Base model loaded successfully")
                    except Exception as fallback_e:
                        print(f"Fallback model also failed: {str(fallback_e)}")
                        self.model = None
                        raise
                else:
                    self.model = None
                    raise
    
    def extract_lyrics(self, audio_path, language=None, vocal_isolation=True):
        """
        Extract lyrics from audio file
        
        Args:
            audio_path: Path to audio file
            language: Target language (None for auto-detection)
            vocal_isolation: Whether to try isolating vocals first
            
        Returns:
            dict: Lyrics extraction results
        """
        try:
            print(f"Extracting lyrics from: {audio_path}")
            
            # Load model lazily
            self._load_model()
            
            if self.model is None:
                return {
                    'text': '',
                    'segments': [],
                    'language': 'unknown',
                    'confidence': 0.0,
                    'error': 'Whisper model not loaded'
                }
            
            # Preprocess audio if needed
            processed_audio_path = self._preprocess_audio(audio_path, vocal_isolation)
            
            # Transcribe using Whisper with enhanced settings for music
            result = self.model.transcribe(
                processed_audio_path,
                language=language,
                word_timestamps=True,
                verbose=False,
                temperature=0.0,  # Use deterministic output
                best_of=5,  # Try multiple attempts and pick best
                beam_size=5,  # Use beam search for better accuracy
                patience=2.0,  # Be more patient with unclear audio
                length_penalty=1.0,  # Don't penalize longer sequences
                suppress_tokens=[-1],  # Suppress non-speech tokens
                initial_prompt="This is a song with vocals and music. Please transcribe only the sung lyrics.",  # Help guide the model
                condition_on_previous_text=False,  # Don't rely on previous context
                fp16=False,  # Use full precision for better quality
                compression_ratio_threshold=2.4,  # Be more lenient with compression
                logprob_threshold=-1.0,  # Be more lenient with log probabilities
                no_speech_threshold=0.6  # Higher threshold to better detect speech vs music
            )
            
            # Extract and format results
            lyrics_data = {
                'text': result['text'].strip(),
                'language': result['language'],
                'segments': self._format_segments(result['segments']),
                'confidence': self._calculate_average_confidence(result['segments']),
                'word_count': len(result['text'].split()) if result['text'] else 0,
                'duration': self._get_total_duration(result['segments'])
            }
            
            # Clean up temporary files
            if processed_audio_path != audio_path:
                try:
                    os.remove(processed_audio_path)
                except:
                    pass
            
            print(f"Lyrics extracted: {len(lyrics_data['text'])} characters")
            print(f"Language: {lyrics_data['language']}")
            print(f"Confidence: {lyrics_data['confidence']:.2f}")
            
            return lyrics_data
            
        except Exception as e:
            print(f"Error extracting lyrics: {str(e)}")
            return {
                'text': '',
                'segments': [],
                'language': 'unknown',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _preprocess_audio(self, audio_path, vocal_isolation=True):
        """
        Preprocess audio for better speech recognition
        
        Args:
            audio_path: Input audio file path
            vocal_isolation: Whether to attempt vocal isolation
            
        Returns:
            str: Path to processed audio file
        """
        try:
            # Load audio with pydub
            audio = AudioSegment.from_file(audio_path)
            
            # Convert to mono first if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Enhanced vocal isolation for stereo sources
            if vocal_isolation:
                try:
                    # Reload as stereo for better vocal isolation
                    stereo_audio = AudioSegment.from_file(audio_path)
                    if stereo_audio.channels == 2:
                        left = stereo_audio.split_to_mono()[0]
                        right = stereo_audio.split_to_mono()[1]
                        
                        # Method 1: Center channel extraction (vocals usually centered)
                        vocals_center = left.overlay(right.invert_phase())
                        
                        # Method 2: Mid-side processing for better isolation
                        mid = (left + right) / 2  # Center channel (vocals)
                        side = (left - right) / 2  # Side channel (instruments)
                        
                        # Enhance center channel while reducing side
                        vocals_enhanced = mid + (mid * 0.5) - (side * 0.3)
                        
                        # Use the enhanced version
                        audio = vocals_enhanced
                except Exception as e:
                    print(f"Advanced vocal isolation failed, using basic: {e}")
                    # Fallback to basic processing
                    pass
            
            # Audio enhancement for speech recognition
            # Normalize volume
            audio = audio.normalize()
            
            # Apply high-pass filter to reduce low-frequency noise (bass, drums)
            # This helps isolate vocals which are typically in mid-high frequencies
            audio = audio.high_pass_filter(80)  # Remove frequencies below 80Hz
            
            # Apply gentle low-pass filter to reduce high-frequency noise
            audio = audio.low_pass_filter(8000)  # Keep frequencies below 8kHz (speech range)
            
            # Boost mid frequencies where vocals typically are (1kHz-4kHz)
            # This is a simple form of vocal enhancement
            audio = audio + 3  # Gentle volume boost
            
            # Set sample rate to 16kHz (optimal for Whisper)
            audio = audio.set_frame_rate(16000)
            
            # Final normalization
            audio = audio.normalize()
            
            # Save processed audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                audio.export(temp_file.name, format='wav')
                return temp_file.name
                
        except Exception as e:
            print(f"Error preprocessing audio: {str(e)}")
            return audio_path  # Return original path if preprocessing fails
    
    def _format_segments(self, segments):
        """Format Whisper segments for consistent output and filter low confidence"""
        formatted_segments = []
        
        for segment in segments:
            segment_confidence = self._get_segment_confidence(segment)
            
            # Only include segments with reasonable confidence (>20% for music)
            if segment_confidence > 0.2:
                formatted_segment = {
                    'start': round(segment['start'], 2),
                    'end': round(segment['end'], 2),
                    'text': segment['text'].strip(),
                    'confidence': segment_confidence
                }
                
                # Add word-level timestamps if available, filtering low confidence words
                if 'words' in segment:
                    high_confidence_words = []
                    for word in segment['words']:
                        word_conf = word.get('probability', 0.5)
                        if word_conf > 0.1 and word['word'].strip():  # Filter very low confidence words
                            high_confidence_words.append({
                                'word': word['word'].strip(),
                                'start': round(word['start'], 2),
                                'end': round(word['end'], 2),
                                'confidence': word_conf
                            })
                    
                    # Only include segment if it has some high-confidence words
                    if high_confidence_words:
                        formatted_segment['words'] = high_confidence_words
                        formatted_segments.append(formatted_segment)
                else:
                    formatted_segments.append(formatted_segment)
        
        return formatted_segments
    
    def _get_segment_confidence(self, segment):
        """Calculate confidence for a segment"""
        if 'words' in segment:
            # Average word probabilities
            word_probs = [word.get('probability', 0.5) for word in segment['words']]
            return sum(word_probs) / len(word_probs) if word_probs else 0.5
        else:
            # Default confidence if no word-level data
            return 0.7
    
    def _calculate_average_confidence(self, segments):
        """Calculate overall confidence score"""
        if not segments:
            return 0.0
        
        total_confidence = 0
        total_duration = 0
        
        for segment in segments:
            duration = segment['end'] - segment['start']
            confidence = self._get_segment_confidence(segment)
            
            total_confidence += confidence * duration
            total_duration += duration
        
        return total_confidence / total_duration if total_duration > 0 else 0.0
    
    def _get_total_duration(self, segments):
        """Get total duration from segments"""
        if not segments:
            return 0.0
        
        return segments[-1]['end'] if segments else 0.0
    
    def extract_lyrics_with_timestamps(self, audio_path, language=None):
        """
        Extract lyrics with detailed timestamps
        
        Args:
            audio_path: Path to audio file
            language: Target language
            
        Returns:
            dict: Detailed lyrics with timestamps
        """
        lyrics_data = self.extract_lyrics(audio_path, language, vocal_isolation=True)
        
        if not lyrics_data['segments']:
            return lyrics_data
        
        # Create formatted output with timestamps
        formatted_lyrics = []
        
        for segment in lyrics_data['segments']:
            start_time = self._format_timestamp(segment['start'])
            end_time = self._format_timestamp(segment['end'])
            text = segment['text'].strip()
            
            if text:
                formatted_lyrics.append(f"[{start_time} - {end_time}] {text}")
        
        lyrics_data['formatted_lyrics'] = '\\n'.join(formatted_lyrics)
        
        return lyrics_data
    
    def _format_timestamp(self, seconds):
        """Format seconds to MM:SS format"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_supported_languages(self):
        """Get list of supported languages"""
        # Whisper supported languages
        return [
            'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr', 'pl', 'ca', 'nl',
            'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi', 'he', 'uk', 'el', 'ms', 'cs', 'ro',
            'da', 'hu', 'ta', 'no', 'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy',
            'sk', 'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk', 'br', 'eu',
            'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw', 'gl', 'mr', 'pa', 'si', 'km',
            'sn', 'yo', 'so', 'af', 'oc', 'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo',
            'uz', 'fo', 'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl', 'mg',
            'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su'
        ]
