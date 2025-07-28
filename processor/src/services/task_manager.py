import json
import os
import threading
from datetime import datetime

class TaskManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TaskManager, cls).__new__(cls)
                    cls._instance._initalized = False
        return cls._instance

    def __init__(self):
        if self._initalized:
            return
        self.jobs = {}
        self.lock = threading.Lock()
        self.jobs_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'jobs.json')
        self._load_jobs()
        self._initalized = True

    def _load_jobs(self):
        try:
            if os.path.exists(self.jobs_file):
                with open(self.jobs_file, 'r') as f:
                    self.jobs = json.load(f)
            else:
                self.jobs = {}
        except Exception as e:
            print(f"Error loading jobs: {str(e)}")
            self.jobs = {}

    def _save_jobs(self):
        try:
            with open(self.jobs_file, 'w') as f:
                json.dump(self.jobs, f, indent=4)
        except Exception as e:
            print(f"Error saving jobs: {str(e)}")

    def create_job(self, job_id, job_data):
        with self.lock:
            self.jobs[job_id] = job_data
            self._save_jobs()

    def get_job(self, job_id):
        return self.jobs.get(job_id)
    
    def update_job_status(self, job_id, status):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]['status'] = status
                self.jobs[job_id]['updated_at'] = datetime.now().isoformat()

            self._save_jobs()