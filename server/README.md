# Recipe Server

A FastAPI server for managing recipes with scraping and structuring capabilities.

## Installation

```bash
# Install dependencies
poetry install

# Run server
poetry run uvicorn server.main:app --reload
```

## Architecture

The server is composed of three main parts:

1. **Recipe Server** (this package)

   - FastAPI server
   - Recipe management
   - Progress tracking
   - Image handling

2. **Recipe Scraper** (package)

   - Web scraping with authentication support
   - Content extraction
   - Image extraction

3. **Recipe Structurer** (package)
   - Content cleaning
   - Recipe structuring with LLMs
   - Graph-based step analysis

## Features

- Extract recipe content from web pages
- Clean and structure recipe data
- Handle authentication for protected recipe sites
- Generate standardized recipe format
- Save recipes with associated images
- Track generation progress
- Manage recipe metadata
- Handle recipe images with multiple sizes

## API Documentation

Once the server is running, visit:

- http://localhost:8000/docs for Swagger UI
- http://localhost:8000/redoc for ReDoc
