from typing import Any, Dict

from starknet_py.net.models.typed_data import TypedData

from exchanges.paradex.types import Order


def build_onboarding_message(chainId: int) -> TypedData:
    message: TypedData = {
        "message": {
            "action": "Onboarding",
        },
        "domain": {"name": "Paradex", "chainId": hex(chainId), "version": "1"},
        "primaryType": "Constant",
        "types": {
            "StarkNetDomain": [
                {"name": "name", "type": "felt"},
                {"name": "chainId", "type": "felt"},
                {"name": "version", "type": "felt"},
            ],
            "Constant": [
                {"name": "action", "type": "felt"},
            ],
        },
    }

    return message


def build_auth_message(chainId: int, now: int, expiry: int) -> TypedData:
    message: TypedData = {
        "message": {
            "method": "POST",
            "path": "/v1/auth",
            "body": "",
            "timestamp": now,
            "expiration": expiry,
        },
        "domain": {"name": "Paradex", "chainId": hex(chainId), "version": "1"},
        "primaryType": "Request",
        "types": {
            "StarkNetDomain": [
                {"name": "name", "type": "felt"},
                {"name": "chainId", "type": "felt"},
                {"name": "version", "type": "felt"},
            ],
            "Request": [
                {"name": "method", "type": "felt"},
                {"name": "path", "type": "felt"},
                {"name": "body", "type": "felt"},
                {"name": "timestamp", "type": "felt"},
                {"name": "expiration", "type": "felt"},
            ],
        },
    }

    return message


def build_stark_key_message(chain_id: int) -> Dict[str, Any]:
    message = {
        "domain": {"name": "Paradex", "version": "1", "chainId": chain_id},
        "primaryType": "Constant",
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            "Constant": [
                {"name": "action", "type": "string"},
            ],
        },
        "message": {
            "action": "STARK Key",
        },
    }

    return message


def build_order_sign_message(chainId: int, order: Order) -> TypedData:
    message: TypedData = {
        "domain": {"name": "Paradex", "chainId": hex(chainId), "version": "1"},
        "primaryType": "Order",
        "types": {
            "StarkNetDomain": [
                {"name": "name", "type": "felt"},
                {"name": "chainId", "type": "felt"},
                {"name": "version", "type": "felt"},
            ],
            "Order": [
                {"name": "timestamp", "type": "felt"},
                {"name": "market", "type": "felt"},
                {"name": "side", "type": "felt"},
                {"name": "orderType", "type": "felt"},
                {"name": "size", "type": "felt"},
                {"name": "price", "type": "felt"},
            ],
        },
        "message": {
            "timestamp": str(order.signature_timestamp),
            "market": order.market,
            "side": order.order_side.chain_side(),
            "orderType": order.order_type.value,
            "size": order.chain_size(),
            "price": order.chain_price(),
        },
    }

    return message
