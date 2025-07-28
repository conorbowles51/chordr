from services.task_manager import TaskManager
from services.audio_processor import AudioProcessor
from utils.validators import validate_audio_file
from flask import Blueprint, jsonify, request, current_app, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os
import threading

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Init services
task_manager = TaskManager()
audio_processor = AudioProcessor()

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
            'upload_time': datetime.now().isoformat(),
            'status': 'uploaded',
            'file_size': os.path.getsize(filepath)
        }    

        # save job
        task_manager.create_job(job_id, job_data)
        
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
    try:
        job_data = task_manager.get_job(job_id)
        if not job_data:
            return jsonify({ 'error': 'Job not found' }), 404
        
        if job_data['status'] != "uploaded":
            return jsonify({ 'error': f'Job status is {job_data["status"]}, cannot process' }), 400
        
        task_manager.update_job_status(job_id, 'processing')

        # Pass the current app to the background thread
        thread = threading.Thread(target=audio_processor.process_audio_async, args=(job_id, current_app._get_current_object()))
        thread.daemon = True
        thread.start()

        return jsonify({
            'job_id': job_id,
            'status': job_data['status'],
            'message': 'Audio processing started'
        }), 202

    except Exception as e:
        current_app.logger.error(f"Processing error: {str(e)}")
        return jsonify({'error': 'Processing failed to start'}), 500

@api_bp.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    try:
        job_data = task_manager.get_job(job_id)
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        # Create response with current job status
        response_data = {
            'job_id': job_id,
            'status': job_data['status'],
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Status check error: {str(e)}")
        return jsonify({'error': 'Failed to get status'}), 500

@api_bp.route('/download/<job_id>', methods=['GET'])
def download_results(job_id):
    try:
        job_data = task_manager.get_job(job_id)
        if not job_data:
            return jsonify({ 'error': 'Job not found' }), 404
        
        if job_data['status'] != 'completed':
            return jsonify({ 'error': 'Job not completed' })
        
        filename = f"{job_id}_results.json"
        filepath = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)

        if not os.path.exists(filepath):
            return jsonify({ 'error': 'File not found' }), 404
        
        return send_file(filepath, as_attachment=True, download_name=filename)

    except Exception as e:
        current_app.logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500