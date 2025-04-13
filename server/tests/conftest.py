import pytest
from aiohttp import web
import base64
import tempfile
import shutil
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Image minimaliste en base64 (1x1 pixel)
FAKE_JPG = base64.b64decode("/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wAALCAABAAEBAREA/8QAJgABAAAAAAAAAAAAAAAAAAAAAxABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAAPwBH/9k=")
FAKE_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect width="100" height="100" fill="red"/>
</svg>""".encode()

# HTML de test pour différents cas
VALID_RECIPE_HTML = """
<html>
    <body>
        <h1>Spaghetti Carbonara</h1>
        <img src="/images/carbonara1.jpg"/>
        <img src="/images/carbonara2.jpg"/>
        <div class="recipe">
            <h2>Ingrédients (4 personnes)</h2>
            <ul>
                <li>400g de spaghetti</li>
                <li>200g de pancetta ou guanciale</li>
                <li>4 gros œufs frais</li>
                <li>100g de parmesan râpé</li>
                <li>50g de pecorino romano râpé</li>
                <li>Poivre noir fraîchement moulu</li>
                <li>Sel</li>
            </ul>
            <h2>Instructions</h2>
            <ol>
                <li>Porter une grande casserole d'eau salée à ébullition. Y cuire les spaghetti al dente selon les instructions du paquet.</li>
                <li>Pendant ce temps, couper la pancetta en lardons et la faire revenir dans une poêle à feu moyen jusqu'à ce qu'elle soit dorée et croustillante.</li>
                <li>Dans un bol, mélanger les œufs, le parmesan, le pecorino et une généreuse dose de poivre noir.</li>
                <li>Quand les pâtes sont cuites, les égoutter en réservant une tasse d'eau de cuisson.</li>
                <li>Verser les pâtes chaudes dans la poêle avec la pancetta, retirer du feu.</li>
                <li>Ajouter rapidement le mélange œufs-fromage en remuant vigoureusement. Si nécessaire, ajouter un peu d'eau de cuisson pour obtenir une sauce crémeuse.</li>
                <li>Servir immédiatement avec du parmesan râpé supplémentaire et du poivre noir.</li>
            </ol>
            <h2>Notes</h2>
            <ul>
                <li>Temps de préparation : 10 minutes</li>
                <li>Temps de cuisson : 15 minutes</li>
                <li>La chaleur des pâtes doit cuire les œufs sans les brouiller</li>
            </ul>
        </div>
    </body>
</html>
"""

INVALID_RECIPE_HTML = """
<html>
    <body>
        <h1>Blog de cuisine</h1>
        <p>Aujourd'hui, parlons de cuisine italienne...</p>
    </body>
</html>
"""

SUB_RECIPE_HTML = """
<html>
    <body>
        <h1>Burger Maison et sa Sauce Spéciale</h1>
        <img src="/images/burger.jpg"/>
        <div class="recipe">
            <h2>Pour la sauce (4 portions)</h2>
            <ul>
                <li>100g de mayonnaise maison</li>
                <li>2 cornichons finement hachés</li>
                <li>1 petit oignon rouge émincé</li>
                <li>1 cuillère à café de paprika fumé</li>
                <li>1 cuillère à café de moutarde de Dijon</li>
                <li>Sel et poivre au goût</li>
            </ul>
            <h2>Pour les burgers (4 portions)</h2>
            <ul>
                <li>600g de bœuf haché (20% de matière grasse)</li>
                <li>4 pains à burger artisanaux</li>
                <li>4 tranches de cheddar affiné</li>
                <li>1 laitue iceberg</li>
                <li>2 tomates mûres</li>
                <li>1 oignon rouge</li>
                <li>Sel et poivre</li>
            </ul>
            <h2>Préparation de la sauce</h2>
            <ol>
                <li>Dans un bol, mélanger la mayonnaise avec les cornichons hachés et l'oignon émincé.</li>
                <li>Ajouter le paprika fumé et la moutarde, bien mélanger.</li>
                <li>Assaisonner avec sel et poivre, réserver au frais.</li>
            </ol>
            <h2>Préparation des burgers</h2>
            <ol>
                <li>Diviser la viande en 4 portions égales (150g chacune) et former des steaks de 1,5cm d'épaisseur.</li>
                <li>Faire un léger creux au centre de chaque steak avec le pouce.</li>
                <li>Saler et poivrer généreusement les deux faces.</li>
                <li>Faire chauffer une poêle ou un grill à feu vif.</li>
                <li>Cuire les steaks 3-4 minutes de chaque côté pour une cuisson médium.</li>
                <li>Ajouter le cheddar sur les steaks en fin de cuisson.</li>
                <li>Toaster légèrement les pains.</li>
                <li>Monter les burgers : pain, sauce, laitue, steak au fromage, tomate, oignon, sauce, pain.</li>
            </ol>
            <h2>Notes</h2>
            <ul>
                <li>Temps de préparation : 20 minutes</li>
                <li>Temps de cuisson : 10 minutes</li>
                <li>La sauce peut être préparée à l'avance</li>
            </ul>
        </div>
    </body>
</html>
"""

async def serve_image(request):
    """Sert une fausse image selon l'extension."""
    if request.path.endswith('.svg'):
        return web.Response(body=FAKE_SVG, content_type='image/svg+xml')
    return web.Response(body=FAKE_JPG, content_type='image/jpeg')

async def serve_recipe(request):
    """Sert le HTML de recette selon l'URL."""
    path = request.path
    if 'carbonara' in path:
        return web.Response(text=VALID_RECIPE_HTML, content_type='text/html')
    elif 'burger' in path:
        return web.Response(text=SUB_RECIPE_HTML, content_type='text/html')
    elif 'blog' in path:
        return web.Response(text=INVALID_RECIPE_HTML, content_type='text/html')
    return web.Response(status=404)

@pytest.fixture
async def test_server(aiohttp_server):
    """Fixture qui démarre un serveur de test."""
    app = web.Application()
    app.router.add_get('/images/{name}', serve_image)
    app.router.add_get('/recipes/{name}', serve_recipe)
    server = await aiohttp_server(app)
    return server

@pytest.fixture
async def temp_dir():
    """Fixture pour créer un dossier temporaire."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

def pytest_configure(config):
    """Configure pytest avec nos marques personnalisées."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    ) 