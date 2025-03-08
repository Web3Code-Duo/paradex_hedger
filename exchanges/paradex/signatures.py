import hashlib
from typing import Any, Dict

from eth_account.messages import encode_typed_data
from web3.auto import w3


def sign_stark_key_message(
    eth_private_key: str, stark_key_message: Dict[str, Any]
) -> str:
    encoded = encode_typed_data(full_message=stark_key_message)
    signed = w3.eth.account.sign_message(encoded, eth_private_key)
    return signed.signature.hex()


def grind_key(key_seed: int, key_value_limit: int) -> int:
    max_allowed_value = 2**256 - (2**256 % key_value_limit)
    current_index = 0

    def indexed_sha256(seed: int, index: int) -> int:
        def padded_hex(x: int) -> str:
            hex_str = hex(x)[2:]
            return hex_str if len(hex_str) % 2 == 0 else "0" + hex_str

        digest = hashlib.sha256(
            bytes.fromhex(padded_hex(seed) + padded_hex(index))
        ).hexdigest()
        return int(digest, 16)

    key = indexed_sha256(seed=key_seed, index=current_index)
    while key >= max_allowed_value:
        current_index += 1
        key = indexed_sha256(seed=key_seed, index=current_index)

    return key % key_value_limit


def get_private_key_from_eth_signature(eth_signature_hex: str) -> int:
    r = eth_signature_hex[2 : 64 + 2]
    return grind_key(
        int(r, 16),
        3618502788666131213697322783095070105526743751716087489154079457884512865583,
    )


def derive_stark_key_from_eth_key(msg: Dict[str, Any], eth_private_key: str) -> int:
    message_signature = sign_stark_key_message(eth_private_key, msg)
    private_key = get_private_key_from_eth_signature(message_signature)
    return private_key
