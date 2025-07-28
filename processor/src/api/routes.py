from utils.validators import validate_audio_file
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({ 'error': 'No file provided' }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({ 'error': 'Invalid file' }), 400
        
        # validate file
        validation_result = validate_audio_file(file)
        if not validation_result['valid']:
            return jsonify({ 'error': validation_result['error'] }), 400
        
        # generate job ID
        job_id = str(uuid.uuid4())

        # save file
        filename = secure_filename(f"{job_id}_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # create job record
        job_data = {
            'job_id': job_id,
            'filename': filename,
            'filepath': filepath,
            'original_filename': file.filename,
            'upload_time': datetime.now(),
            'status': 'uploaded',
            'file_size': os.path.getsize(filepath)
        }    

        # TODO: Give job to task manager
        
        return jsonify({
            'job_id': job_id,
            'message': 'File uploaded successfully',
            'filename': file.filename,
            'status': 'uploaded',
            'file_size': job_data['file_size']
        }), 200
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

@api_bp.route('/process/<job_id>', methods=['POST'])
def process_audio(job_id):
    return jsonify({
        "message": "process"
    })

@api_bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    return jsonify({
        "message": f"status {job_id}"
    })

@api_bp.route('/download/<job_id>', methods=['GET'])
def get_results(job_id):
    return jsonify({
        "message": f"download {job_id}"
    })