"""Main router module."""
from fastapi import APIRouter
from .routes import recipes, authors

router = APIRouter()

router.include_router(
    recipes.router,
    prefix="/recipes",
    tags=["recipes"]
)

router.include_router(
    authors.router,
    prefix="/authors",
    tags=["authors"]
) 