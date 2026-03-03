from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
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
        "server:app",  # Utiliser le format d'import string pour permettre le hot reload
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=120,  # Augmentation du timeout keep-alive (défaut: 5 secondes)
        timeout_graceful_shutdown=60,  # Augmentation du timeout d'arrêt gracieux
        limit_concurrency=100,  # Limite de connexions simultanées
        limit_max_requests=10000,  # Limite de requêtes maximum
        reload=True,  # Activation du hot reload pour le développement
    )