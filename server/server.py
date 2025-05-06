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

if __name__ == "__main__":
    import uvicorn
    
    # Configuration d'Uvicorn avec des timeouts augmentés
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=120,  # Augmentation du timeout keep-alive (défaut: 5 secondes)
        timeout_graceful_shutdown=60,  # Augmentation du timeout d'arrêt gracieux
        limit_concurrency=100,  # Limite de connexions simultanées
        limit_max_requests=10000,  # Limite de requêtes maximum
    )