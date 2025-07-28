from flask import Flask, jsonify
from flask_cors import CORS
from config.settings import Config
from api.routes import api_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # For development purposes
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Local storage for uploads and ouput for the time being
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

    app.register_blueprint(api_bp)

    return app

app = create_app()

@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to Chordr Audio Processing API",
        "version": "0.0.1",
        "endpoints": {
            "upload": "/api/upload",
            "process": "/api/process/<job_id>",
            "status": "/api/status/<job_id>",
            "download": "/api/download/<job_id>"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 