from http.server import BaseHTTPRequestHandler
import json
import os
from apps.storage import Repo
from apps.scheduler.main import crawl_hospital


class handler(BaseHTTPRequestHandler):
    """Serverless function to register hospital and trigger initial crawl."""

    def _send_response(self, status_code: int, data: dict):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', os.environ.get('VERCEL_ALLOWED_ORIGINS', '*'))
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self._send_response(200, {})

    def do_POST(self):
        """Handle POST request to register hospital."""
        try:
            # Verify internal API token
            auth_header = self.headers.get('Authorization', '')
            expected_token = os.environ.get('REV_INTERNAL_API_TOKEN', '')

            if expected_token and not auth_header.endswith(expected_token):
                self._send_response(401, {'error': 'Unauthorized'})
                return

            # Parse request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))

            hospital_name = body.get('name')
            naver_place_url = body.get('naver_place_url')

            if not hospital_name or not naver_place_url:
                self._send_response(400, {
                    'error': 'Missing required fields: name, naver_place_url'
                })
                return

            # Check if hospital already exists
            existing = Repo.get_hospital_by_url(naver_place_url)
            if existing:
                self._send_response(400, {
                    'error': 'Hospital with this URL already registered',
                    'hospital_id': str(existing.id)
                })
                return

            # Create hospital
            hospital = Repo.create_hospital(hospital_name, naver_place_url)

            # Trigger initial crawl (first 10 reviews)
            crawl_hospital.delay(str(hospital.id), naver_place_url, is_initial=True)

            self._send_response(201, {
                'success': True,
                'hospital_id': str(hospital.id),
                'name': hospital.name,
                'message': 'Hospital registered and initial crawl queued'
            })

        except json.JSONDecodeError:
            self._send_response(400, {'error': 'Invalid JSON'})
        except Exception as e:
            self._send_response(500, {'error': str(e)})
