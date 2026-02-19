from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.recipes import router as recipes_router
from api.routes.auth import router as auth_router
from api.routes.images import router as images_router
from api.routes.constants import router as constants_router
from api.routes.authors import router as authors_router
from api.routes.recipe_files import router as recipe_files_router
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

# Configuration du port
port = int(os.getenv("PORT", "3001"))

app = FastAPI(title="Recipe API")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://recipes.tfrere.com",
        "http://recipes.tfrere.com",
        "https://recipes-api.tfrere.com",
        "http://recipes-api.tfrere.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

# Inclure les routers
app.include_router(recipes_router)
app.include_router(auth_router)
app.include_router(images_router)
app.include_router(constants_router)
app.include_router(authors_router)
app.include_router(recipe_files_router)

@app.get("/api/debug-paths")
async def debug_paths():
    import glob as g
    from api.dependencies import get_recipe_service
    try:
        service = get_recipe_service()
        return {
            "cwd": os.getcwd(),
            "base_path": str(service.base_path),
            "base_path_abs": str(service.base_path.absolute()),
            "recipes_path": str(service.recipes_path),
            "recipes_path_abs": str(service.recipes_path.absolute()),
            "recipes_path_exists": service.recipes_path.exists(),
            "recipe_count": len(g.glob(os.path.join(service.recipes_path, "*.recipe.json"))),
            "has_url_index": hasattr(service, '_url_index'),
            "app_exists": os.path.exists('/app'),
            "app_data_recipes_exists": os.path.exists('/app/data/recipes'),
            "app_data_recipes_count": len(g.glob('/app/data/recipes/*.recipe.json')),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    
    # Configuration d'Uvicorn avec des timeouts augmentés
    uvicorn.run(
        "server:app",  # Utiliser le format d'import string pour permettre le hot reload
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=120,  # Augmentation du timeout keep-alive (défaut: 5 secondes)
        timeout_graceful_shutdown=60,  # Augmentation du timeout d'arrêt gracieux
        limit_concurrency=100,  # Limite de connexions simultanées
        limit_max_requests=10000,  # Limite de requêtes maximum
        reload=True,  # Activation du hot reload pour le développement
    )