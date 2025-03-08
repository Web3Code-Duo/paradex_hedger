import asyncio

from loguru import logger
from web3.auto import w3

from config import PRIVATE_KEY
from exchanges.bitget.api import BitgetAPI
from exchanges.paradex.account import generate_paradex_account
from exchanges.paradex.api import ParadexAPI
from hedger import HedgeManager

eth_account = w3.eth.account.from_key(PRIVATE_KEY)


async def main() -> None:
    paradex_api = ParadexAPI()
    bitget_api = BitgetAPI()

    config = await paradex_api.get_config()

    paradex_account_address, paradex_account_private_key_hex = generate_paradex_account(
        config, PRIVATE_KEY
    )

    await paradex_api.perform_onboarding(
        paradex_account_address,
        paradex_account_private_key_hex,
        eth_account.address,
    )

    await paradex_api.get_jwt_token(
        paradex_account_address,
        paradex_account_private_key_hex,
    )

    hedge_manager = HedgeManager(paradex_api, bitget_api)
    
    paradex_order, bitget_order = await hedge_manager.execute_hedge_strategy(
        paradex_account_address, paradex_account_private_key_hex
    )

    logger.info("Hedging strategy executed successfully")
    logger.info(f"Paradex order: {paradex_order}")
    logger.info(f"Bitget order: {bitget_order}")


if __name__ == "__main__":
    asyncio.run(main())
