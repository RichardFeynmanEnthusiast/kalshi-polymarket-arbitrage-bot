class NoDataFound(Exception):
    """Raised when no data is found in database, and upstream logic relies on it"""
    def __init__(self, message):
        super().__init__(message)
        self.message = message
    def __str__(self):
        return f"{self.message}"