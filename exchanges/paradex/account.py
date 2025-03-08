from typing import Dict, Tuple

from starknet_py.common import int_from_bytes
from starknet_py.hash.address import compute_address
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.account.account import Account
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.signer.stark_curve_signer import KeyPair

from .messages import (
    build_stark_key_message,
)
from .signatures import (
    derive_stark_key_from_eth_key,
)


def get_acc_contract_address_and_call_data(
    proxy_contract_hash: str,
    account_class_hash: str,
    public_key: str,
) -> str:
    calldata = [
        int(account_class_hash, 16),
        get_selector_from_name("initialize"),
        2,
        int(public_key, 16),
        0,
    ]

    address = compute_address(
        class_hash=int(proxy_contract_hash, 16),
        constructor_calldata=calldata,
        salt=int(public_key, 16),
    )
    return hex(address)


def generate_paradex_account(
    paradex_config: Dict, eth_account_private_key_hex: str
) -> Tuple[str, str]:
    eth_chain_id = int(paradex_config["l1_chain_id"])
    stark_key_msg = build_stark_key_message(eth_chain_id)
    paradex_private_key = derive_stark_key_from_eth_key(
        stark_key_msg, eth_account_private_key_hex
    )
    paradex_key_pair = KeyPair.from_private_key(paradex_private_key)
    paradex_account_private_key_hex = hex(paradex_private_key)
    paradex_account_address = get_acc_contract_address_and_call_data(
        paradex_config["paraclear_account_proxy_hash"],
        paradex_config["paraclear_account_hash"],
        hex(paradex_key_pair.public_key),
    )
    return paradex_account_address, paradex_account_private_key_hex


def get_account(
    account_address: str, account_key: str, paradex_config: Dict
) -> Account:
    client = FullNodeClient(node_url=paradex_config["starknet_fullnode_rpc_url"])
    key_pair = KeyPair.from_private_key(key=int(account_key, 16))
    chain_id = paradex_config["starknet_chain_id"]
    chain = int_from_bytes(chain_id.encode())

    account = Account(
        client=client,
        address=account_address,
        key_pair=key_pair,
        chain=chain,  # type: ignore
    )
    return account
