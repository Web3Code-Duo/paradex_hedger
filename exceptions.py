class ExchangeError(Exception):
    def __init__(self, message: str = "Exchange operation error") -> None:
        self.message = message
        super().__init__(self.message)


class InsufficientFundsError(ExchangeError):
    def __init__(self, message: str = "Insufficient funds for operation") -> None:
        self.message = message
        super().__init__(self.message)


class OrderSizeError(ExchangeError):
    def __init__(self, message: str = "Invalid order size") -> None:
        self.message = message
        super().__init__(self.message)


class OrderSizeTooSmallError(OrderSizeError):
    def __init__(self, message: str = "Order size is too small") -> None:
        self.message = message
        super().__init__(self.message)


class OrderSizeTooLargeError(OrderSizeError):
    def __init__(self, message: str = "Order size is too large") -> None:
        self.message = message
        super().__init__(self.message)


class OrderCancelledError(ExchangeError):
    def __init__(self, message: str = "Order was cancelled") -> None:
        self.message = message
        super().__init__(self.message)


class HedgeError(ExchangeError):
    def __init__(self, message: str = "Hedging operation error") -> None:
        self.message = message
        super().__init__(self.message)


class ParadexError(HedgeError):
    def __init__(self, message: str = "Paradex operation error") -> None:
        self.message = message
        super().__init__(self.message)


class BitgetError(HedgeError):
    def __init__(self, message: str = "Bitget operation error") -> None:
        self.message = message
        super().__init__(self.message)


class HedgePositionMismatchError(HedgeError):
    def __init__(self, message: str = "Hedging error: one position opened, other failed") -> None:
        self.message = message
        super().__init__(self.message)
