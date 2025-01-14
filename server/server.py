from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.recipes import router as recipes_router
from api.routes.auth import router as auth_router
from api.routes.images import router as images_router
from api.routes.constants import router as constants_router
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

app = FastAPI(title="Recipe API")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://recipes.tfrere.com",
        "http://recipes.tfrere.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

# Inclure les routers
app.include_router(recipes_router)
app.include_router(auth_router)
app.include_router(images_router)
app.include_router(constants_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3001"))
    uvicorn.run(app, host="0.0.0.0", port=port)