"""cTrader Open API Client - Protobuf over TCP/TLS"""
import socket
import ssl
import struct
import threading
import time
from typing import Optional

from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import (
    ProtoMessage,
    ProtoHeartbeatEvent,
)
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAApplicationAuthRes,
    ProtoOAAccountAuthReq,
    ProtoOAAccountAuthRes,
    ProtoOAGetAccountListByAccessTokenReq,
    ProtoOAGetAccountListByAccessTokenRes,
    ProtoOATraderReq,
    ProtoOATraderRes,
    ProtoOAAssetListReq,
    ProtoOAAssetListRes,
    ProtoOAReconcileReq,
    ProtoOAReconcileRes,
    ProtoOADealListReq,
    ProtoOADealListRes,
    ProtoOACashFlowHistoryListReq,
    ProtoOACashFlowHistoryListRes,
    ProtoOAErrorRes,
)
from config.logging import logger

HEARTBEAT_TYPE = 51
ERROR_TYPE = 2142


class CTraderClient:
    """TCP/TLS client for cTrader Open API using Protobuf encoding.

    Connects to cTrader Open API via raw TCP socket with TLS and
    sends/receives length-prefixed Protobuf messages.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: Optional[ssl.SSLSocket] = None
        self._msg_id = 0
        self._lock = threading.Lock()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.sock is not None

    def connect(self) -> bool:
        """Connect to cTrader via TCP/TLS"""
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            raw_sock = socket.create_connection((self.host, self.port), timeout=15)
            self.sock = ctx.wrap_socket(raw_sock, server_hostname=self.host)
            self._connected = True
            logger.info("cTrader TCP connected", host=self.host, port=self.port)
            return True
        except Exception as e:
            logger.error("cTrader TCP connection failed", error=str(e))
            self._connected = False
            return False

    def disconnect(self):
        """Close TCP connection"""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self._connected = False
        self.sock = None
        logger.info("cTrader TCP disconnected")

    def _next_msg_id(self) -> str:
        with self._lock:
            self._msg_id += 1
            return str(self._msg_id)

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Read exactly n bytes from socket"""
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _send_proto(self, message) -> str:
        """Send a protobuf message wrapped in ProtoMessage with length prefix"""
        msg_id = self._next_msg_id()
        wrapper = ProtoMessage()
        wrapper.payloadType = message.payloadType
        wrapper.payload = message.SerializeToString()
        wrapper.clientMsgId = msg_id

        data = wrapper.SerializeToString()
        length_prefix = struct.pack(">I", len(data))
        self.sock.sendall(length_prefix + data)
        return msg_id

    def _recv_proto(self, timeout: float = 15.0) -> Optional[ProtoMessage]:
        """Receive a length-prefixed ProtoMessage"""
        self.sock.settimeout(timeout)
        length_data = self._recv_exact(4)
        if not length_data:
            return None
        length = struct.unpack(">I", length_data)[0]
        msg_data = self._recv_exact(length)
        if not msg_data:
            return None
        msg = ProtoMessage()
        msg.ParseFromString(msg_data)
        return msg

    def _send_request(self, request_msg, response_type: int,
                      timeout: float = 15.0) -> Optional[bytes]:
        """Send request and wait for matching response payload.

        Returns the raw payload bytes of the response, or None on error.
        """
        if not self.is_connected:
            return None

        try:
            self._send_proto(request_msg)

            deadline = time.time() + timeout
            while time.time() < deadline:
                remaining = max(1.0, deadline - time.time())
                msg = self._recv_proto(timeout=remaining)
                if msg is None:
                    self._connected = False
                    return None

                # Handle heartbeat
                if msg.payloadType == HEARTBEAT_TYPE:
                    hb = ProtoHeartbeatEvent()
                    self._send_proto(hb)
                    continue

                # Handle error
                if msg.payloadType == ERROR_TYPE:
                    err = ProtoOAErrorRes()
                    err.ParseFromString(msg.payload)
                    logger.error("cTrader API error",
                                 error_code=err.errorCode,
                                 description=err.description if err.HasField("description") else "")
                    return None

                # Check for expected response
                if msg.payloadType == response_type:
                    return msg.payload

                logger.debug("cTrader skipping message", payload_type=msg.payloadType)

        except Exception as e:
            logger.error("cTrader request failed", error=str(e))
            self._connected = False
            return None

        logger.error("cTrader request timeout")
        return None

    # ── API Methods ──────────────────────────────────────────

    def application_auth(self, client_id: str, client_secret: str) -> bool:
        """Authenticate the application"""
        req = ProtoOAApplicationAuthReq()
        req.clientId = client_id
        req.clientSecret = client_secret

        payload = self._send_request(req, ProtoOAApplicationAuthRes().payloadType)
        if payload is not None:
            logger.info("cTrader application authenticated")
            return True
        return False

    def get_accounts_by_token(self, access_token: str) -> list[dict]:
        """Get account list for access token.

        Returns list of dicts with:
        - ctidTraderAccountId: int
        - traderLogin: int
        - isLive: bool
        """
        req = ProtoOAGetAccountListByAccessTokenReq()
        req.accessToken = access_token

        payload = self._send_request(
            req, ProtoOAGetAccountListByAccessTokenRes().payloadType
        )
        if not payload:
            return []

        res = ProtoOAGetAccountListByAccessTokenRes()
        res.ParseFromString(payload)

        accounts = []
        for acc in res.ctidTraderAccount:
            accounts.append({
                "ctidTraderAccountId": acc.ctidTraderAccountId,
                "traderLogin": acc.traderLogin,
                "isLive": acc.isLive,
            })
        return accounts

    def account_auth(self, ctid_trader_account_id: int, access_token: str) -> bool:
        """Authenticate a trading account"""
        req = ProtoOAAccountAuthReq()
        req.ctidTraderAccountId = ctid_trader_account_id
        req.accessToken = access_token

        payload = self._send_request(req, ProtoOAAccountAuthRes().payloadType)
        return payload is not None

    def get_trader(self, ctid_trader_account_id: int) -> Optional[dict]:
        """Get trader account info.

        Returns dict with: balance, moneyDigits, leverageInCents,
        depositAssetId, registrationTimestamp, etc.
        """
        req = ProtoOATraderReq()
        req.ctidTraderAccountId = ctid_trader_account_id

        payload = self._send_request(req, ProtoOATraderRes().payloadType)
        if not payload:
            return None

        res = ProtoOATraderRes()
        res.ParseFromString(payload)
        trader = res.trader

        return {
            "balance": trader.balance,
            "moneyDigits": trader.moneyDigits,
            "leverageInCents": trader.leverageInCents,
            "depositAssetId": trader.depositAssetId,
            "registrationTimestamp": trader.registrationTimestamp,
        }

    def get_asset_list(self, ctid_trader_account_id: int) -> dict[int, str]:
        """Get asset list for the account. Returns mapping of assetId -> name (e.g. 'USD', 'EUR')."""
        req = ProtoOAAssetListReq()
        req.ctidTraderAccountId = ctid_trader_account_id

        payload = self._send_request(req, ProtoOAAssetListRes().payloadType)
        if not payload:
            return {}

        res = ProtoOAAssetListRes()
        res.ParseFromString(payload)

        return {asset.assetId: asset.name for asset in res.asset}

    def get_reconcile(self, ctid_trader_account_id: int) -> Optional[dict]:
        """Get open positions and pending orders.

        Returns dict with:
        - position: list of position dicts
        - order: list of order dicts
        """
        req = ProtoOAReconcileReq()
        req.ctidTraderAccountId = ctid_trader_account_id

        payload = self._send_request(req, ProtoOAReconcileRes().payloadType)
        if not payload:
            return None

        res = ProtoOAReconcileRes()
        res.ParseFromString(payload)

        positions = []
        for pos in res.position:
            positions.append({
                "swap": pos.swap,
                "commission": pos.commission,
                "unrealizedPnl": pos.unrealizedPnl if pos.HasField("unrealizedPnl") else 0,
            })

        return {"position": positions, "order": list(res.order)}

    def get_cashflow_history(self, ctid_trader_account_id: int,
                             from_timestamp_ms: int,
                             to_timestamp_ms: int) -> list[dict]:
        """Get cash flow history (deposits/withdrawals/copy operations).

        Returns list of dicts with: operationType, delta, externalNote, moneyDigits.
        Max window: 7 days imposed by the API.
        """
        req = ProtoOACashFlowHistoryListReq()
        req.ctidTraderAccountId = ctid_trader_account_id
        req.fromTimestamp = from_timestamp_ms
        req.toTimestamp = to_timestamp_ms

        payload = self._send_request(
            req, ProtoOACashFlowHistoryListRes().payloadType, timeout=15.0
        )
        if not payload:
            return []

        res = ProtoOACashFlowHistoryListRes()
        res.ParseFromString(payload)

        items = []
        for dw in res.depositWithdraw:
            items.append({
                "operationType": dw.operationType,
                "delta": dw.delta,
                "balance": dw.balance,
                "equity": dw.equity if dw.HasField("equity") else 0,
                "changeBalanceTimestamp": dw.changeBalanceTimestamp if dw.HasField("changeBalanceTimestamp") else 0,
                "externalNote": dw.externalNote if dw.HasField("externalNote") else "",
                "moneyDigits": dw.moneyDigits if dw.HasField("moneyDigits") else 2,
            })
        return items

    def get_deal_list(self, ctid_trader_account_id: int,
                      from_timestamp_ms: int, to_timestamp_ms: int) -> Optional[dict]:
        """Get closed deals history.

        Returns dict with:
        - deal: list of deal dicts
        - hasMore: bool
        """
        req = ProtoOADealListReq()
        req.ctidTraderAccountId = ctid_trader_account_id
        req.fromTimestamp = from_timestamp_ms
        req.toTimestamp = to_timestamp_ms

        payload = self._send_request(
            req, ProtoOADealListRes().payloadType, timeout=30.0
        )
        if not payload:
            return None

        res = ProtoOADealListRes()
        res.ParseFromString(payload)

        deals = []
        for deal in res.deal:
            deal_dict = {
                "dealId": deal.dealId,
                "orderId": deal.orderId,
                "positionId": deal.positionId,
                "volume": deal.volume,
                "filledVolume": deal.filledVolume,
                "dealStatus": str(deal.dealStatus),
                "tradeSide": str(deal.tradeSide),
                "commission": deal.commission if deal.HasField("commission") else 0,
            }

            # Close position details
            if deal.HasField("closePositionDetail"):
                cpd = deal.closePositionDetail
                deal_dict["closePositionDetail"] = {
                    "grossProfit": cpd.grossProfit,
                    "swap": cpd.swap,
                    "commission": cpd.commission,
                    "balance": cpd.balance,
                }

            deals.append(deal_dict)

        return {
            "deal": deals,
            "hasMore": res.hasMore,
        }
