import base64
import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any, Dict, Tuple

import aiohttp
from loguru import logger

from config import BITGET_API_KEY, BITGET_API_PASSPHRASE, BITGET_API_SECRET
from exchanges.bitget.exceptions import BitgetAPIError


class BitgetAPI:
    def __init__(self) -> None:
        self.api_key = BITGET_API_KEY
        self.api_secret = BITGET_API_SECRET
        self.api_passphrase = BITGET_API_PASSPHRASE
        self.base_url = "https://api.bitget.com"

    def _create_signature(
        self, method: str, path: str, data: Dict[str, Any]
    ) -> Tuple[str, str]:
        data = data or {}
        timestamp = str(int(time.time() * 1000))

        if method.upper() == "GET" and data:
            query_string = urllib.parse.urlencode(data)
            full_path = f"{path}?{query_string}"
            message = f"{timestamp}{method.upper()}{full_path}"
        else:
            message = f"{timestamp}{method.upper()}{path}"
            if data:
                message += json.dumps(data)

        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode(), message.encode(), hashlib.sha256
            ).digest()
        ).decode()

        return signature, timestamp

    def _create_headers(
        self, method: str, path: str, data: Dict[str, Any]
    ) -> Dict[str, str]:
        signature, timestamp = self._create_signature(method, path, data)

        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.api_passphrase,
        }

    async def _make_request(
        self, method: str, path: str, data: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        headers = self._create_headers(method, path, data)
        url = f"{self.base_url}{path}"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                headers=headers,
                params=data if method == "GET" else None,
                json=data if method != "GET" else None,
            ) as response:
                status_code = response.status

                try:
                    response_data = await response.json()
                except aiohttp.ContentTypeError:
                    response_data = {}

                if not (200 <= status_code < 300):
                    logger.error(f"Unable to [{method}] {path}")
                    logger.error(f"Status Code: {status_code}")
                    logger.error(f"Response Text: {response_data}")
                    raise BitgetAPIError()

                return response_data

    async def get_account_details(
        self, symbol: str, product_type: str = "USDC-FUTURES", margin_coin: str = "USDC"
    ) -> Dict[str, Any]:
        data = {
            "symbol": symbol,
            "productType": product_type,
            "marginCoin": margin_coin,
        }
        response = await self._make_request("GET", "/api/v2/mix/account/account", data)
        return response

    async def set_position_mode(
        self, product_type: str = "USDC-FUTURES", position_mode: str = "one_way_mode"
    ) -> Dict[str, Any]:
        data = {
            "productType": product_type,
            "posMode": position_mode,
        }
        response = await self._make_request(
            "POST", "/api/v2/mix/account/set-position-mode", data
        )
        return response

    async def set_margin_mode(
        self,
        symbol: str,
        product_type: str = "USDC-FUTURES",
        margin_coin: str = "USDC",
        margin_mode: str = "isolated",
    ):
        data = {
            "symbol": symbol,
            "productType": product_type,
            "marginCoin": margin_coin,
            "marginMode": margin_mode,
        }
        response = await self._make_request(
            "POST", "/api/v2/mix/account/set-margin-mode", data
        )
        return response

    async def set_leverage(
        self,
        symbol: str,
        leverage: int,
        product_type: str = "USDC-FUTURES",
        margin_coin: str = "USDC",
        hold_side: str | None = None,
    ) -> Dict[str, Any]:
        data = {
            "symbol": symbol,
            "productType": product_type,
            "marginCoin": margin_coin,
            "leverage": leverage,
        }

        if hold_side:
            data["holdSide"] = hold_side

        response = await self._make_request(
            "POST", "/api/v2/mix/account/set-leverage", data
        )
        return response

    async def get_future_price(
        self, symbol: str, product_type: str = "USDC-FUTURES"
    ) -> Dict[str, Any]:
        data = {
            "symbol": symbol,
            "productType": product_type,
        }
        response = await self._make_request(
            "GET", "/api/v2/mix/market/symbol-price", data
        )
        return response

    async def get_contract_details(
        self, symbol: str, product_type: str = "USDC-FUTURES"
    ) -> Dict[str, Any]:
        data = {
            "symbol": symbol,
            "productType": product_type,
        }
        response = await self._make_request("GET", "/api/v2/mix/market/contracts", data)
        return response

    async def place_order(
        self,
        symbol: str,
        size: str,
        side: str,
        order_type: str = "market",
        product_type: str = "USDC-FUTURES",
        margin_coin: str = "USDC",
        margin_mode: str = "isolated",
    ) -> Dict[str, Any]:
        data = {
            "symbol": symbol,
            "marginCoin": margin_coin,
            "marginMode": margin_mode,
            "size": size,
            "side": side,
            "orderType": order_type,
            "productType": product_type,
        }
        response = await self._make_request(
            "POST", "/api/v2/mix/order/place-order", data
        )
        return response

    async def get_open_interest(
        self, symbol: str, product_type: str = "USDC-FUTURES"
    ) -> Dict[str, Any]:
        data = {
            "symbol": symbol,
            "productType": product_type,
        }
        response = await self._make_request(
            "GET", "/api/v2/mix/market/open-interest", data
        )
        return response

    async def cancel_order(self, symbol: str, order_id: str, product_type: str = "USDC-FUTURES") -> Dict[str, Any]:
        data = {
            "symbol": symbol,
            "productType": product_type,
            "orderId": order_id,
        }
        response = await self._make_request(
            "POST", "/api/v2/mix/order/cancel-order", data
        )
        return response
