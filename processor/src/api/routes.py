from flask import Blueprint, jsonify

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/upload', methods=['POST'])
def upload_file():
    return jsonify({
        "message": "upload"
    })

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