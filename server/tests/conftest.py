import pytest


def pytest_configure(config):
    """Configure pytest avec nos marques personnalisées."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
