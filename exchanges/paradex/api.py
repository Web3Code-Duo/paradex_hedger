import time
from typing import Any, Dict, Optional, Tuple

import aiohttp
from loguru import logger
from starknet_py.common import int_from_bytes

from exchanges.paradex.exceptions import ParadexAPIError
from exchanges.paradex.types import Order

from .account import get_account
from .messages import (
    build_auth_message,
    build_onboarding_message,
    build_order_sign_message,
)
from .utils import flatten_signature, is_token_expired


class ParadexAPI:
    BASE_URL = "https://api.prod.paradex.trade/v1"

    def __init__(
        self,
        account_address: Optional[str] = None,
        private_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
    ):
        self.jwt_token = jwt_token
        self.account_address = account_address
        self.private_key = private_key
        self.config: Dict[str, Any] = {}

    async def _create_headers(self) -> Dict[str, str]:
        if not self.jwt_token:
            return {}
        return {"Authorization": f"Bearer {self.jwt_token}"}

    async def _make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        check_jwt: bool = True,
    ) -> Tuple[aiohttp.ClientResponse, bool]:
        url = f"{self.BASE_URL}{path}"
        if headers is None:
            headers = await self._create_headers()

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, headers=headers, json=data
            ) as response:
                status_code = response.status

                try:
                    response_data = await response.json()
                except aiohttp.ContentTypeError:
                    response_data = {}

                if check_jwt:
                    await self._check_token_expiry(status_code, response_data)

                if not (200 <= status_code < 300):
                    return response, False

                return response, True

    async def get_config(self) -> Dict[str, Any]:
        method = "GET"
        path = "/system/config"
        response, success = await self._make_request(method, path, check_jwt=False)

        response_status = response.status
        response_data = await response.json()

        if success:
            self.config = await response.json()
            return response_data

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to get Paradex API configuration")

    async def get_jwt_token(self, account_address: str, private_key: str) -> str:
        if not self.config:
            await self.get_config()

        self.account_address = account_address
        self.private_key = private_key

        chain = int_from_bytes(self.config["starknet_chain_id"].encode())
        account = get_account(
            account_address=account_address,
            account_key=private_key,
            paradex_config=self.config,
        )

        now = int(time.time())
        expiry = now + 24 * 60 * 60
        message = build_auth_message(chain, now, expiry)
        sig = account.sign_message(message)

        method = "POST"
        path = "/auth"

        headers = {
            "PARADEX-STARKNET-ACCOUNT": account_address,
            "PARADEX-STARKNET-SIGNATURE": flatten_signature(sig),
            "PARADEX-TIMESTAMP": str(now),
            "PARADEX-SIGNATURE-EXPIRATION": str(expiry),
        }

        response, success = await self._make_request(
            method, path, headers=headers, check_jwt=False
        )

        response_status = response.status
        response_data = await response.json()

        if success:
            self.jwt_token = response_data.get("jwt_token", "")
            return self.jwt_token

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to get JWT token")

    async def perform_onboarding(
        self, account_address: str, private_key: str, ethereum_account: str
    ) -> None:
        if not self.config:
            await self.get_config()

        chain_id = int_from_bytes(self.config["starknet_chain_id"].encode())
        account = get_account(account_address, private_key, self.config)

        message = build_onboarding_message(chain_id)
        sig = account.sign_message(message)

        method = "POST"
        path = "/onboarding"

        headers = {
            "PARADEX-ETHEREUM-ACCOUNT": ethereum_account,
            "PARADEX-STARKNET-ACCOUNT": account_address,
            "PARADEX-STARKNET-SIGNATURE": flatten_signature(sig),
        }

        body = {
            "public_key": hex(account.signer.public_key),
            "referral_code": "boldwhale88",
        }

        await self._make_request(
            method, path, headers=headers, data=body, check_jwt=False
        )

    async def get_account_info(self) -> Dict[str, Any]:
        method = "GET"
        path = "/account"

        response, success = await self._make_request(method, path)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to get account info")

    async def get_margin_configuration(self, market: str) -> Dict[str, Any]:
        method = "GET"
        path = f"/account/margin/?market={market}"

        response, success = await self._make_request(method, path)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to get margin configuration")

    async def set_margin_configuration(
        self, market: str, leverage: int, margin_type: str
    ) -> Dict[str, Any]:
        method = "POST"
        path = f"/account/margin/{market}"
        data = {"leverage": leverage, "marginType": margin_type}

        response, success = await self._make_request(method, path, data=data)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to set margin configuration")

    async def place_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        method = "POST"
        path = "/orders"

        response, success = await self._make_request(method, path, data=payload)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to place order")

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        method = "DELETE"
        path = f"/orders/{order_id}"

        response, success = await self._make_request(method, path)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data

        if response_data.get("error", "") == "ORDER_IS_CLOSED":
            return {"error": "ORDER_IS_CLOSED"}

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to cancel order")

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        method = "GET"
        path = f"/orders/{order_id}"

        response, success = await self._make_request(method, path)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to get order")

    async def get_bbo(self, market: str) -> Dict[str, Any]:
        method = "GET"
        path = f"/bbo/{market}"

        response, success = await self._make_request(method, path, check_jwt=False)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to get BBO")

    async def get_market_data(self, market: Optional[str] = None) -> Dict[str, Any]:
        method = "GET"
        path = f"/markets/?market={market}" if market else "/markets/"

        response, success = await self._make_request(method, path, check_jwt=False)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data["results"][0]

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to get market data")

    async def update_max_slippage(self, max_slippage: str) -> Dict[str, Any]:
        method = "POST"
        path = "/v1/account/profile/max_slippage"
        data = {"max_slippage": max_slippage}

        response, success = await self._make_request(method, path, data=data)

        response_status = response.status
        response_data = await response.json()

        if success:
            return response_data

        logger.error(f"Unable to [{method}] {path}")
        logger.error(f"Status Code: {response_status}")
        logger.error(f"Response Text: {response_data}")
        raise ParadexAPIError("Failed to update max slippage")

    def sign_order(
        self, order: Order, paradex_address: str, paradex_private_key: str
    ) -> str:
        if not self.config:
            raise ParadexAPIError("Config not initialized. Call get_config() first")

        account = get_account(paradex_address, paradex_private_key, self.config)
        message = build_order_sign_message(
            int_from_bytes(self.config["starknet_chain_id"].encode()), order
        )

        sig = account.sign_message(message)
        return flatten_signature(sig)

    async def _check_token_expiry(
        self, status_code: int, response_data: Dict[str, Any]
    ) -> None:
        if is_token_expired(status_code, response_data):
            logger.warning("JWT token has expired, attempting to refresh...")
            if not self.account_address or not self.private_key:
                logger.error(
                    "Cannot refresh token: account_address or private_key not provided"
                )
                raise ParadexAPIError("Token expired and no credentials to refresh")
            await self.get_jwt_token(self.account_address, self.private_key)
            logger.info("JWT token refreshed successfully")
