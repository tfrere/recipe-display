import pytest

# Configuration pour permettre les tests asynchrones
pytest_plugins = ["pytest_asyncio"]

# Configurer le marquage asyncio par défaut pour tous les tests
def pytest_collection_modifyitems(items):
    """Ajoute le marqueur asyncio à tous les tests qui utilisent asyncio"""
    for item in items:
        if item.get_closest_marker("asyncio") is None:
            if "async" in item.name or "await" in item.name:
                item.add_marker(pytest.mark.asyncio) 