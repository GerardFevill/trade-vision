"""cTrader Open API WebSocket Client - JSON protocol over WebSocket"""
import json
import ssl
import threading
import time
from typing import Optional
from config.logging import logger


class PayloadType:
    """cTrader Open API v2 payload types"""
    # Proto
    HEARTBEAT_EVENT = 51
    ERROR_RES = 50
    # Application auth
    OA_APPLICATION_AUTH_REQ = 2100
    OA_APPLICATION_AUTH_RES = 2101
    # Account auth
    OA_ACCOUNT_AUTH_REQ = 2102
    OA_ACCOUNT_AUTH_RES = 2103
    # Trader info
    OA_TRADER_REQ = 2121
    OA_TRADER_RES = 2122
    # Reconcile (open positions + pending orders)
    OA_RECONCILE_REQ = 2124
    OA_RECONCILE_RES = 2125
    # Deal list (closed trades history)
    OA_DEAL_LIST_REQ = 2133
    OA_DEAL_LIST_RES = 2134
    # Account list by access token
    OA_GET_ACCOUNT_LIST_REQ = 2149
    OA_GET_ACCOUNT_LIST_RES = 2150
    # Symbols
    OA_SYMBOL_BY_ID_REQ = 2114
    OA_SYMBOL_BY_ID_RES = 2115


class CTraderClient:
    """WebSocket client for cTrader Open API using JSON encoding.

    Connects to cTrader Open API via WebSocket and sends/receives
    JSON-encoded messages (text frames).
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.url = f"wss://{host}:{port}"
        self.ws = None
        self._msg_id = 0
        self._lock = threading.Lock()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.ws is not None

    def connect(self) -> bool:
        """Connect to cTrader WebSocket API"""
        try:
            import websocket
            self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
            self.ws.settimeout(15)
            self.ws.connect(self.url)
            self._connected = True
            logger.info("cTrader WebSocket connected", url=self.url)
            return True
        except Exception as e:
            logger.error("cTrader WebSocket connection failed", url=self.url, error=str(e))
            self._connected = False
            return False

    def disconnect(self):
        """Close WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self._connected = False
        self.ws = None
        logger.info("cTrader WebSocket disconnected")

    def _next_msg_id(self) -> str:
        with self._lock:
            self._msg_id += 1
            return str(self._msg_id)

    def _send_request(self, payload_type: int, payload: dict,
                      expected_response_type: int = None,
                      timeout: float = 15.0) -> Optional[dict]:
        """Send a request and wait for the matching response.

        Args:
            payload_type: Request message type
            payload: Message payload as dict
            expected_response_type: Expected response type (default: payload_type + 1)
            timeout: Response timeout in seconds

        Returns:
            Response payload dict or None on error
        """
        if not self.is_connected:
            return None

        if expected_response_type is None:
            expected_response_type = payload_type + 1

        msg_id = self._next_msg_id()
        message = {
            "clientMsgId": msg_id,
            "payloadType": payload_type,
            "payload": payload
        }

        try:
            self.ws.settimeout(timeout)
            self.ws.send(json.dumps(message))

            deadline = time.time() + timeout
            while time.time() < deadline:
                raw = self.ws.recv()
                if not raw:
                    continue

                response = json.loads(raw)
                resp_type = response.get("payloadType")

                # Handle heartbeat
                if resp_type == PayloadType.HEARTBEAT_EVENT:
                    self.ws.send(json.dumps({"payloadType": PayloadType.HEARTBEAT_EVENT}))
                    continue

                # Handle error
                if resp_type == PayloadType.ERROR_RES:
                    err = response.get("payload", {})
                    logger.error("cTrader API error",
                                 error_code=err.get("errorCode"),
                                 description=err.get("description"),
                                 maintenance=err.get("maintenanceEndTimestamp"))
                    return None

                # Check for expected response
                if resp_type == expected_response_type:
                    return response.get("payload", {})

                # Skip unexpected messages (events, etc.)
                logger.debug("cTrader unexpected message", payload_type=resp_type)

        except Exception as e:
            logger.error("cTrader request failed",
                         payload_type=payload_type, error=str(e))
            self._connected = False
            return None

        logger.error("cTrader request timeout", payload_type=payload_type)
        return None

    # ── API Methods ──────────────────────────────────────────

    def application_auth(self, client_id: str, client_secret: str) -> bool:
        """Authenticate the application (ProtoOAApplicationAuthReq)"""
        result = self._send_request(
            PayloadType.OA_APPLICATION_AUTH_REQ,
            {"clientId": client_id, "clientSecret": client_secret}
        )
        if result is not None:
            logger.info("cTrader application authenticated")
            return True
        return False

    def get_accounts_by_token(self, access_token: str) -> list[dict]:
        """Get account list for access token (ProtoOAGetAccountListByAccessTokenReq)

        Returns list of ctidTraderAccount objects with:
        - ctidTraderAccountId: int (API account ID)
        - traderLogin: int (visible login number)
        - isLive: bool
        """
        result = self._send_request(
            PayloadType.OA_GET_ACCOUNT_LIST_REQ,
            {"accessToken": access_token}
        )
        if result:
            return result.get("ctidTraderAccount", [])
        return []

    def account_auth(self, ctid_trader_account_id: int, access_token: str) -> bool:
        """Authenticate a trading account (ProtoOAAccountAuthReq)"""
        result = self._send_request(
            PayloadType.OA_ACCOUNT_AUTH_REQ,
            {
                "ctidTraderAccountId": ctid_trader_account_id,
                "accessToken": access_token
            }
        )
        return result is not None

    def get_trader(self, ctid_trader_account_id: int) -> Optional[dict]:
        """Get trader account info (ProtoOATraderReq)

        Returns trader object with:
        - balance: int (in cents, divide by 10^moneyDigits)
        - moneyDigits: int (typically 2)
        - leverageInCents: int
        - depositAssetId: int
        - registrationTimestamp: int
        - totalMarginCalculationType: int
        """
        return self._send_request(
            PayloadType.OA_TRADER_REQ,
            {"ctidTraderAccountId": ctid_trader_account_id}
        )

    def get_reconcile(self, ctid_trader_account_id: int) -> Optional[dict]:
        """Get open positions and pending orders (ProtoOAReconcileReq)

        Returns:
        - position: list of open positions
        - order: list of pending orders
        """
        return self._send_request(
            PayloadType.OA_RECONCILE_REQ,
            {"ctidTraderAccountId": ctid_trader_account_id}
        )

    def get_deal_list(self, ctid_trader_account_id: int,
                      from_timestamp_ms: int, to_timestamp_ms: int) -> Optional[dict]:
        """Get closed deals history (ProtoOADealListReq)

        Args:
            ctid_trader_account_id: Account ID
            from_timestamp_ms: Start time in milliseconds
            to_timestamp_ms: End time in milliseconds

        Returns:
        - deal: list of deal objects
        - hasMore: bool
        """
        return self._send_request(
            PayloadType.OA_DEAL_LIST_REQ,
            {
                "ctidTraderAccountId": ctid_trader_account_id,
                "fromTimestamp": from_timestamp_ms,
                "toTimestamp": to_timestamp_ms,
            },
            timeout=30.0
        )
