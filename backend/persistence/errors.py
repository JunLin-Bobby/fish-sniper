"""Persistence-layer errors surfaced to HTTP handlers."""


class FishSniperPersistenceUnavailableError(Exception):
    """Raised when the database client cannot complete an operation reliably."""
