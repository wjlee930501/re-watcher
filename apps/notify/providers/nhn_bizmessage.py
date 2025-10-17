import httpx
import uuid
from typing import Dict, Optional
from apps.common import settings, get_logger

logger = get_logger(__name__)


class NHNBizMessageProvider:
    """NHN Cloud Bizmessage AlimTalk API provider with connection pooling."""

    # Shared HTTP client for connection pooling
    _client: Optional[httpx.AsyncClient] = None

    def __init__(self):
        self.appkey = settings.alim_appkey
        self.secret = settings.alim_secret
        self.sender_key = settings.alim_sender_key
        self.base_url = f"https://api-alimtalk.cloud.toast.com/alimtalk/v2.3/appkeys/{self.appkey}/messages"

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get or create shared HTTP client for connection pooling."""
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return cls._client

    async def send_alimtalk(
        self,
        template_code: str,
        recipient_phone: str,
        params: Dict[str, str],
        idempotency_key: Optional[str] = None
    ) -> Dict:
        """
        Send AlimTalk message via NHN Cloud.

        Args:
            template_code: Template code
            recipient_phone: Recipient phone number (E.164 format)
            params: Template parameters
            idempotency_key: Idempotency key for deduplication

        Returns:
            dict: Response with request_id and status
        """
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Prepare request
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Secret-Key": self.secret,
            "X-NC-API-IDEMPOTENCY-KEY": idempotency_key
        }

        body = {
            "senderKey": self.sender_key,
            "templateCode": template_code,
            "recipientList": [
                {
                    "recipientNo": recipient_phone,
                    "templateParameter": params
                }
            ]
        }

        try:
            # Use shared client for connection pooling
            client = await self.get_client()
            response = await client.post(
                self.base_url,
                json=body,
                headers=headers
            )

            response_data = response.json()

                if response.status_code == 200:
                    # Extract request ID and result
                    request_id = response_data.get("header", {}).get("requestId")
                    send_results = response_data.get("sendResults", [])

                    if send_results:
                        result = send_results[0]
                        result_code = result.get("resultCode")
                        result_message = result.get("resultMessage")

                        if result_code == "0000":
                            logger.info(f"AlimTalk sent successfully: {request_id}")
                            return {
                                "success": True,
                                "request_id": request_id,
                                "result_code": result_code,
                                "result_message": result_message
                            }
                        else:
                            logger.error(
                                f"AlimTalk send failed: {result_code} - {result_message}"
                            )
                            return {
                                "success": False,
                                "request_id": request_id,
                                "result_code": result_code,
                                "result_message": result_message
                            }

                logger.error(f"Unexpected response format: {response_data}")
                return {
                    "success": False,
                    "error": "Unexpected response format"
                }

        except httpx.TimeoutException:
            logger.error("AlimTalk request timeout")
            return {
                "success": False,
                "error": "Request timeout"
            }
        except Exception as e:
            logger.error(f"AlimTalk send error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
