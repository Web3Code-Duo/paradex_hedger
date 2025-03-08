import random
from decimal import Decimal
from typing import Literal, Optional, Sequence, Tuple


def calculate_position_value(
    min_trade_amount: Decimal,
    position_usd_limits: Sequence[float | int],
    available_balance: Decimal,
) -> Optional[Decimal]:
    min_limit = Decimal(position_usd_limits[0])
    max_limit = Decimal(position_usd_limits[1])

    min_position = max(min_trade_amount, min_limit)
    max_position = min(max_limit, available_balance)

    if min_position > max_position:
        return None

    random_position = Decimal(
        str(random.uniform(float(min_position), float(max_position)))
    )

    return random_position


def get_random_order_side() -> Tuple[Literal["buy", "sell"], Literal["long", "short"]]:
    if random.choice([True, False]):
        return "buy", "long"
    else:
        return "sell", "short"
