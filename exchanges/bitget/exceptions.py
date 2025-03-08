class BitgetAPIError(Exception):
    def __init__(
        self, message: str = "An error occurred while interacting with Bitget API"
    ):
        self.message = message
        super().__init__(self.message)
