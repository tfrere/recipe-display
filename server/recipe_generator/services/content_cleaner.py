from typing import Optional, Callable, Awaitable, Any
from pathlib import Path
import json
import os
from datetime import datetime
from ..models.web_content import WebContent
from ..prompts.cleanup_recipe import format_cleanup_recipe_prompt
from ..utils.error_utils import save_error_to_file
from ..config import load_config
from ..models.text_content import TextContent
from ..llm.base import LLMProvider

class ContentCleaner:
    """Service for cleaning and organizing recipe content."""
    
    def __init__(self, provider: LLMProvider):
        """
        Initialise le service.
        
        Args:
            provider: Provider LLM à utiliser
        """
        self.provider = provider
        self.config = load_config()
        
    async def clean_content(
        self,
        web_content: WebContent,
        on_progress: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> WebContent:
        """Clean up and organize recipe content."""
        print("\nStarting content cleaning")  # Debug
        
        # Format prompt
        prompt = format_cleanup_recipe_prompt(
            content=web_content.main_content,
            image_urls=web_content.image_urls
        )
        
        print("\nSending prompt to LLM")  # Debug
        content = ""
        
        try:
            async for chunk in self.provider.generate_stream(
                prompt=prompt,
                temperature=self.config["temperature"]
            ):
                # Add to accumulated content
                content += chunk
                
                # Update progress if callback provided
                if on_progress:
                    await on_progress(content)
            
            print("\nCleaned content:")
            print("---START OF CLEANED CONTENT---")
            print(content)
            print("---END OF CLEANED CONTENT---\n")
            
            # Check for validation error
            first_line = content.split('\n')[0].strip()
            if first_line == "VALIDATION_ERROR":
                print("Validation error detected")  # Debug
                error_data = {
                    "error_type": "validation_error",
                    "error_message": content,
                    "input_data": {
                        "title": web_content.title,
                        "content": web_content.main_content,
                        "image_urls": web_content.image_urls
                    }
                }
                save_error_to_file(error_data)
                raise ValueError(content)
            
            # Extract selected image URL
            selected_image_url = ""
            try:
                # Look for SELECTED IMAGE URL section
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == "SELECTED IMAGE URL:":
                        if i + 1 < len(lines):
                            selected_image_url = lines[i + 1].strip()
                            print(f"Found selected image URL: {selected_image_url}")  # Debug
                            break
                
                print(f"\nSelected image URL: {selected_image_url}")
                
                # Verify selected URL is in available URLs
                if selected_image_url and selected_image_url not in web_content.image_urls:
                    print("⚠️ WARNING: Selected URL is not in available URLs!")
                    print("Looking for a similar URL...")
                    
                    # Try to find a similar URL
                    recipe_name = web_content.title.lower()
                    for url in web_content.image_urls:
                        if any(word in url.lower() for word in recipe_name.split()):
                            selected_image_url = url
                            print(f"Similar URL found: {url}")
                            break
                    else:
                        if web_content.image_urls:
                            selected_image_url = web_content.image_urls[0]
                            print("No similar URL found, using first available URL.")
                        else:
                            selected_image_url = ""
                            print("No image URLs available.")
                
            except Exception as e:
                print(f"Error extracting image URL: {str(e)}")
                selected_image_url = ""
            
            # Update web content with cleaned content and selected image
            web_content.main_content = content
            web_content.selected_image_url = selected_image_url
            
            print("Content cleaning completed successfully")  # Debug
            return web_content
            
        except Exception as e:
            print(f"Error in content cleaning: {str(e)}")
            raise
            
    async def clean_text_content(
        self,
        text: str,
        on_progress: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """
        Nettoie le contenu textuel d'une recette.
        
        Args:
            text: Texte à nettoyer
            on_progress: Callback pour le suivi de la progression
            
        Returns:
            Texte nettoyé
        """
        # Construit le prompt
        prompt = f"""You are a recipe content cleaner. Your task is to clean and format recipe content.

Please follow these rules:
1. Keep the original language of the recipe (French or English)
2. Keep all measurements and units as they are
3. Keep all cooking times and temperatures as they are
4. Keep all ingredient quantities as they are
5. Keep all special characters (*, -, etc.) as they are
6. Keep all formatting (bold, italic, etc.) as it is
7. Keep all section titles (TITLE, NOTES, etc.) in English

The output should be formatted like this:
TITLE:
[Recipe title]

NOTES:
[Any notes about the recipe, including source, tips, etc.]
---

METADATA:
NATIONALITY: [Recipe origin/nationality]
AUTHOR: [Recipe author if available]
BOOK: [Book name if from a book]
QUALITY_SCORE: [A score from 0 to 100 based on completeness and clarity]

SELECTED IMAGE URL:
[URL of the main recipe image if available]

SPECIAL EQUIPMENT:
[List of special equipment needed, one per line with -]

INGREDIENTS:
[List of ingredients, one per line with -]

INSTRUCTIONS:
[Numbered list of instructions]

Here's the content to clean:

{text}

Please clean and format this content according to the rules above."""
        
        try:
            content = ""
            print("[DEBUG] Starting content cleaning...")
            
            async for chunk in self.provider.generate_stream(
                prompt=prompt,
                temperature=self.config["temperature"]
            ):
                
                # Si c'est un message d'usage des tokens, on le passe directement au callback
                if isinstance(chunk, str) and chunk.startswith("__TOKEN_USAGE__"):
                    if on_progress:
                        await on_progress(chunk)
                    continue
                
                # Sinon c'est du contenu normal
                if isinstance(chunk, str):
                    content += chunk
                    if on_progress:
                        await on_progress(chunk)
            
            
            # Vérifie que le contenu est bien formaté
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            
            # Cherche les sections requises
            has_title = False
            has_ingredients = False
            has_instructions = False
            
            for line in lines:
                if line.startswith("TITLE:"):
                    has_title = True
                    print("[DEBUG] Found TITLE section")
                elif line.startswith("INGREDIENTS:"):
                    has_ingredients = True
                    print("[DEBUG] Found INGREDIENTS section")
                elif line.startswith("INSTRUCTIONS:"):
                    has_instructions = True
                    print("[DEBUG] Found INSTRUCTIONS section")
            
            errors = []
            if not has_title:
                errors.append("Response must start with TITLE section")
            if not has_ingredients:
                errors.append("Response must contain INGREDIENTS section")
            if not has_instructions:
                errors.append("Response must contain INSTRUCTIONS section")
            
            if errors:
                print(f"[DEBUG] Validation errors found: {errors}")
                raise ValueError("VALIDATION_ERROR: " + "; ".join(errors))
            
            print("[DEBUG] Content validation successful")
            return content
            
        except Exception as e:
            print(f"[DEBUG] Error occurred: {str(e)}")
            # Sauvegarde l'erreur pour debug
            error_dir = Path(__file__).parent.parent.parent / "data" / "errors"
            error_dir.mkdir(exist_ok=True, parents=True)
            
            error_data = {
                "error": str(e),
                "prompt": prompt,
                "content": content if 'content' in locals() else None
            }
            
            error_file = error_dir / f"error_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}.json"
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
            
            print(f"Error data saved to: {error_file}")
            raise ValueError(f"VALIDATION_ERROR: {str(e)}")