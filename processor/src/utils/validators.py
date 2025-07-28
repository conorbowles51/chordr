import os
from werkzeug.datastructures import FileStorage
from flask import current_app

def validate_audio_file(file):
  
    if not file or not file.filename:
        return {'valid': False, 'error': 'No file provided'}
    
    # Check file extension
    allowed_extensions = {'mp3', 'wav', 'flac', 'm4a', 'ogg', 'aac'}
    file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_extension not in allowed_extensions:
        return {
            'valid': False, 
            'error': f'File type .{file_extension} not supported. Allowed types: {", ".join(allowed_extensions)}'
        }
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer
    
    max_size = current_app.config['MAX_UPLOAD_SIZE']
    if file_size > max_size:
        return {
            'valid': False,
            'error': f'File too large. Maximum size: {max_size // (1024*1024)}MB, got: {file_size // (1024*1024)}MB'
        }
    
    if file_size == 0:
        return {'valid': False, 'error': 'File is empty'}
    
    return {'valid': True, 'error': None}