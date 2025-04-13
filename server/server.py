from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.recipes import router as recipes_router
from api.routes.auth import router as auth_router
from api.routes.images import router as images_router
from api.routes.constants import router as constants_router
from api.routes.authors import router as authors_router
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)