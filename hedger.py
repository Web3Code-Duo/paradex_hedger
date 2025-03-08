import time
from decimal import ROUND_UP, Decimal
from typing import Optional, Tuple

from loguru import logger

from config import POSITION_USD_LIMITS
from exceptions import (
    BitgetError,
    InsufficientFundsError,
    OrderCancelledError,
    ParadexError,
)
from exchanges.bitget.api import BitgetAPI
from exchanges.paradex.api import ParadexAPI
from exchanges.paradex.types import Order, OrderSide, OrderType
from utils import calculate_position_value, get_random_order_side


class HedgeManager:
    def __init__(self, paradex_api: ParadexAPI, bitget_api: BitgetAPI) -> None:
        self.paradex_api = paradex_api
        self.bitget_api = bitget_api

    async def prepare_paradex(self) -> Decimal:
        account_info = await self.paradex_api.get_account_info()
        available_balance = Decimal(account_info["free_collateral"])

        margin_configuration = (
            await self.paradex_api.get_margin_configuration("ETH-USD-PERP")
        )["configs"][0]

        if (margin_configuration["leverage"] != 1) or (
            margin_configuration["margin_type"] != "ISOLATED"
        ):
            await self.paradex_api.set_margin_configuration(
                market="ETH-USD-PERP",
                leverage=1,
                margin_type="ISOLATED",
            )

        return available_balance

    async def prepare_bitget(self) -> Decimal:
        account_details = await self.bitget_api.get_account_details("ETHPERP")
        available_balance = Decimal(account_details["data"]["isolatedMaxAvailable"])
        margin_mode = account_details["data"]["marginMode"]
        position_mode = account_details["data"]["posMode"]
        isolated_long_lever = account_details["data"]["isolatedLongLever"]
        isolated_short_lever = account_details["data"]["isolatedShortLever"]

        if position_mode != "one_way_mode":
            await self.bitget_api.set_position_mode()

        if margin_mode != "isolated":
            await self.bitget_api.set_margin_mode("ETHPERP")

        if isolated_long_lever != 1 or isolated_short_lever != 1:
            await self.bitget_api.set_leverage("ETHPERP", 1)

        return available_balance

    async def place_paradex_order(
        self,
        order_side: OrderSide,
        size: Decimal,
        paradex_account_address: str,
        paradex_account_private_key_hex: str,
        reduce_only: bool = False,
    ) -> str:
        order = Order(
            market="ETH-USD-PERP",
            order_type=OrderType.Market,
            order_side=order_side,
            size=size,
            signature_timestamp=int(time.time()) * 1_000,
            flags=["REDUCE_ONLY"] if reduce_only else [],
        )

        order.signature = self.paradex_api.sign_order(
            order,
            paradex_account_address,
            paradex_account_private_key_hex,
        )

        order_response = await self.paradex_api.place_order(order.dump_to_dict())
        order_id = order_response["id"]

        created_order = await self.paradex_api.get_order(order_id)

        cancel_reason = created_order.get("cancel_reason")
        if cancel_reason:
            raise OrderCancelledError(cancel_reason)

        return order_id

    async def place_bitget_order(
        self, side: str, size: Decimal
    ) -> str:
        order_response = await self.bitget_api.place_order(
            symbol="ETHPERP",
            size=str(size),
            side=side,
        )

        if order_response["msg"] != "success":
            raise OrderCancelledError()

        return order_response["data"]["orderId"]

    async def execute_hedge_strategy(
        self, paradex_account_address: str, paradex_account_private_key_hex: str
    ) -> Tuple[str, str]:
        try:
            paradex_balance = await self.prepare_paradex() * Decimal(0.95)
            bitget_balance = await self.prepare_bitget() * Decimal(0.95)

            bitget_side, bitget_direction = get_random_order_side()
            paradex_side = OrderSide.Sell if bitget_side == "buy" else OrderSide.Buy
            paradex_direction = "short" if bitget_direction == "long" else "long"

            bbo = await self.paradex_api.get_bbo("ETH-USD-PERP")
            paradex_price = Decimal(
                bbo["ask"] if paradex_side == OrderSide.Buy else bbo["bid"]
            )

            bitget_price_data = await self.bitget_api.get_future_price("ETHPERP")
            if not bitget_price_data.get("data"):
                raise BitgetError("Failed to get Bitget price data")
            bitget_price = Decimal(bitget_price_data["data"][0]["markPrice"])

            market_data = await self.paradex_api.get_market_data("ETH-USD-PERP")
            paradex_increment = Decimal(market_data["order_size_increment"])
            min_notional_paradex = Decimal(market_data["min_notional"])
            min_paradex_size = self._calculate_min_paradex_size(
                min_notional_paradex, paradex_price, paradex_increment
            )
            max_paradex_size = Decimal(market_data["max_order_size"])

            contract_details = await self.bitget_api.get_contract_details("ETHPERP")
            if not contract_details.get("data"):
                raise BitgetError("Failed to get Bitget contract details")

            contract_data = contract_details["data"][0]
            bitget_multiplier = Decimal(contract_data["sizeMultiplier"])
            min_notional_bitget = Decimal(contract_data["minTradeUSDT"])
            min_bitget_size = Decimal(contract_data["minTradeNum"])

            bitget_open_interests = await self.bitget_api.get_open_interest("ETHPERP")
            if not bitget_open_interests.get("data") or not bitget_open_interests[
                "data"
            ].get("openInterestList"):
                raise BitgetError("Failed to get Bitget open interest data")

            bitget_open_interest = Decimal(
                bitget_open_interests["data"]["openInterestList"][0]["size"]
            )
            max_bitget_size = self._calculate_max_bitget_size(
                Decimal(contract_data["posLimit"]),
                bitget_open_interest,
                bitget_multiplier,
            )

            self._validate_size_constraints(
                min_paradex_size, max_paradex_size, min_bitget_size, max_bitget_size
            )

            min_available_balance = min(paradex_balance, bitget_balance)
            min_trade_amount = max(min_notional_paradex, min_notional_bitget)
            position_value = calculate_position_value(
                min_trade_amount, POSITION_USD_LIMITS, min_available_balance
            )
            if position_value is None:
                raise InsufficientFundsError(
                    "Insufficient funds on one of the exchanges"
                )

            paradex_size = (
                (position_value / paradex_price) // paradex_increment
            ) * paradex_increment
            bitget_size = (
                (position_value / bitget_price) // bitget_multiplier
            ) * bitget_multiplier

            max_affordable_paradex_size = min(
                (paradex_balance / paradex_price)
                // paradex_increment
                * paradex_increment,
                max_paradex_size,
            )
            max_affordable_bitget_size = min(
                (bitget_balance / bitget_price)
                // bitget_multiplier
                * bitget_multiplier,
                max_bitget_size,
            )

            common_size = self._find_common_size(
                paradex_size,
                bitget_size,
                paradex_increment,
                bitget_multiplier,
                min_paradex_size,
                min_bitget_size,
                max_affordable_paradex_size,
                max_affordable_bitget_size,
            )

            if common_size:
                paradex_size = bitget_size = common_size
            else:
                paradex_size = min(
                    paradex_size, max_paradex_size, max_affordable_paradex_size
                )
                bitget_size = min(
                    bitget_size, max_bitget_size, max_affordable_bitget_size
                )

            self._validate_final_sizes(
                paradex_size,
                bitget_size,
                min_paradex_size,
                min_bitget_size,
                paradex_price,
                bitget_price,
                paradex_balance,
                bitget_balance,
            )

            return await self.place_orders(
                paradex_side,
                paradex_direction,
                paradex_size,
                paradex_account_address,
                paradex_account_private_key_hex,
                bitget_side,
                bitget_direction,
                bitget_size,
            )

        except Exception as error:
            logger.error(f"Execution failed: {str(error)}")
            raise

    def _calculate_min_paradex_size(
        self, min_notional: Decimal, price: Decimal, increment: Decimal
    ) -> Decimal:
        min_size_from_notional = (min_notional / price) * Decimal(1.05)
        return (min_size_from_notional / increment).to_integral_value(
            rounding=ROUND_UP
        ) * increment

    def _calculate_max_bitget_size(
        self, position_limit: Decimal, open_interest: Decimal, multiplier: Decimal
    ) -> Decimal:
        return (
            (position_limit * open_interest * Decimal("0.95")) // multiplier
        ) * multiplier

    def _validate_size_constraints(
        self,
        min_paradex_size: Decimal,
        max_paradex_size: Decimal,
        min_bitget_size: Decimal,
        max_bitget_size: Decimal,
    ) -> None:
        if max_paradex_size < min_paradex_size:
            raise ValueError(
                f"Paradex max order size ({max_paradex_size}) is less than min order size ({min_paradex_size})"
            )
        if max_bitget_size < min_bitget_size:
            raise ValueError(
                f"Bitget max order size ({max_bitget_size}) is less than min order size ({min_bitget_size})"
            )

    def _find_common_size(
        self,
        paradex_size: Decimal,
        bitget_size: Decimal,
        paradex_increment: Decimal,
        bitget_multiplier: Decimal,
        min_paradex_size: Decimal,
        min_bitget_size: Decimal,
        max_affordable_paradex_size: Decimal,
        max_affordable_bitget_size: Decimal,
    ) -> Optional[Decimal]:
        upper_limit = min(max_affordable_paradex_size, max_affordable_bitget_size)
        min_size = max(min_paradex_size, min_bitget_size)
        increment_step = min(paradex_increment, bitget_multiplier)
        target_size = max(paradex_size, bitget_size)

        current_size = min_size
        while current_size <= upper_limit:
            if (current_size % paradex_increment == 0) and (
                current_size % bitget_multiplier == 0
            ):
                if current_size >= target_size:
                    return current_size
            current_size += increment_step

        current_size = upper_limit
        while current_size >= min_size:
            if (current_size % paradex_increment == 0) and (
                current_size % bitget_multiplier == 0
            ):
                return current_size
            current_size -= increment_step

        return None

    def _validate_final_sizes(
        self,
        paradex_size: Decimal,
        bitget_size: Decimal,
        min_paradex_size: Decimal,
        min_bitget_size: Decimal,
        paradex_price: Decimal,
        bitget_price: Decimal,
        paradex_balance: Decimal,
        bitget_balance: Decimal,
    ) -> None:
        if paradex_size < min_paradex_size:
            raise ValueError(
                f"Calculated Paradex size ({paradex_size}) is less than minimum ({min_paradex_size})"
            )
        if bitget_size < min_bitget_size:
            raise ValueError(
                f"Calculated Bitget size ({bitget_size}) is less than minimum ({min_bitget_size})"
            )

        paradex_cost = paradex_size * paradex_price
        bitget_cost = bitget_size * bitget_price

        if paradex_cost > paradex_balance or bitget_cost > bitget_balance:
            raise InsufficientFundsError(
                f"Calculated size exceeds available balance. "
                f"Paradex: cost {paradex_cost} > balance {paradex_balance}, "
                f"Bitget: cost {bitget_cost} > balance {bitget_balance}"
            )

    async def place_orders(
        self,
        paradex_side: OrderSide,
        paradex_direction: str,
        paradex_size: Decimal,
        paradex_account_address: str,
        paradex_account_private_key_hex: str,
        bitget_side: str,
        position_direction: str,
        bitget_size: Decimal,
    ) -> Tuple[str, str]:
        logger.info(
            f"Executing hedge: Paradex {paradex_direction.upper()} {paradex_size} ETH, "
            f"Bitget {position_direction.upper()} {bitget_size} ETH"
        )

        try:
            paradex_order_id = await self.place_paradex_order(
                paradex_side,
                paradex_size,
                paradex_account_address,
                paradex_account_private_key_hex,
            )

            logger.info("Paradex order placed")

            try:
                bitget_order_id = await self.place_bitget_order(
                    bitget_side, bitget_size
                )

                logger.info("Bitget order placed")

                return paradex_order_id, bitget_order_id

            except OrderCancelledError:
                cancel_order_response = await self.paradex_api.cancel_order(
                    paradex_order_id
                )
                if cancel_order_response.get("error", "") == "ORDER_IS_CLOSED":
                    await self.place_paradex_order(
                        OrderSide.Sell
                        if paradex_side == OrderSide.Buy
                        else OrderSide.Buy,
                        paradex_size,
                        paradex_account_address,
                        paradex_account_private_key_hex,
                        reduce_only=True,
                    )
                    logger.info("Paradex position closed")
                else:
                    logger.info("Paradex order cancelled")

                raise

            except Exception as error:
                cancel_order_response = await self.paradex_api.cancel_order(
                    paradex_order_id
                )
                if cancel_order_response.get("error", "") == "ORDER_IS_CLOSED":
                    await self.place_paradex_order(
                        OrderSide.Sell
                        if paradex_side == OrderSide.Buy
                        else OrderSide.Buy,
                        paradex_size,
                        paradex_account_address,
                        paradex_account_private_key_hex,
                        reduce_only=True,
                    )
                    logger.info("Paradex position closed")
                else:
                    logger.info("Paradex order cancelled")

                raise BitgetError(f"Bitget order failed: {str(error)}")

        except OrderCancelledError:
            raise

        except Exception as error:
            raise ParadexError(f"Paradex order failed: {str(error)}") from error
