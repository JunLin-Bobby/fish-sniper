"""Weather domain errors."""


class FishSniperWeatherUnavailableError(Exception):
    """Raised when live weather cannot be fetched or parsed."""
