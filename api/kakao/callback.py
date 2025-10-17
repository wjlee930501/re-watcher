from http.server import BaseHTTPRequestHandler
import json
import os
from apps.storage import Repo
from apps.common import get_logger

logger = get_logger(__name__)


class handler(BaseHTTPRequestHandler):
    """Serverless function to handle KakaoTalk notification callbacks."""

    def _send_response(self, status_code: int, data: dict = None):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if data:
            self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_POST(self):
        """Handle POST callback from Kakao/NHN."""
        try:
            # Verify callback token
            verify_token = self.headers.get('X-Verify-Token', '')
            expected_token = os.environ.get('REV_CALLBACK_VERIFY_TOKEN', '')

            if expected_token and verify_token != expected_token:
                logger.warning(f"Invalid callback token received")
                self._send_response(401, {'error': 'Unauthorized'})
                return

            # Parse request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))

            logger.info(f"Received callback: {body}")

            # Extract callback data (format varies by provider)
            request_id = body.get('requestId') or body.get('request_id')
            result_code = body.get('resultCode') or body.get('result_code') or body.get('code')
            result_message = body.get('resultMessage') or body.get('result_message') or body.get('message')

            if not request_id:
                logger.error("No requestId in callback")
                self._send_response(400, {'error': 'Missing requestId'})
                return

            # Determine status from result code
            status = 'failed'
            if result_code in ['0000', '200', 'success']:
                status = 'delivered'
            elif result_code in ['3000', '3001']:  # Recipient unavailable
                status = 'failed'

            # Update notification log
            # Note: In a production system, you'd query by request_id
            # For now, we'll log the callback
            logger.info(
                f"Callback received - requestId: {request_id}, "
                f"resultCode: {result_code}, status: {status}"
            )

            # TODO: Implement proper request_id to notification_log mapping
            # Repo.update_notification_status(log_id, status, result_code, result_message)

            self._send_response(200, {'success': True})

        except json.JSONDecodeError:
            logger.error("Invalid JSON in callback")
            self._send_response(400, {'error': 'Invalid JSON'})
        except Exception as e:
            logger.error(f"Callback error: {e}")
            self._send_response(500, {'error': str(e)})
