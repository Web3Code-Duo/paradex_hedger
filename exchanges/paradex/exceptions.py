class ParadexAPIError(Exception):
    def __init__(
        self, message: str = "An error occurred while interacting with Paradex API"
    ) -> None:
        self.message = message
        super().__init__(self.message)
