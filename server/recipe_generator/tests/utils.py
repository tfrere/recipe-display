from typing import Optional
from pathlib import Path

class StreamDiffService:
    """Service pour afficher uniquement les différences dans un stream de texte."""
    
    def __init__(self):
        self._last_text = ""
    
    def update(self, new_text: str) -> str:
        """
        Compare avec le dernier texte reçu et retourne uniquement la nouvelle partie.
        
        Args:
            new_text: Nouveau texte complet reçu
            
        Returns:
            La partie du texte qui n'a pas encore été affichée
        """
        # Si le nouveau texte est plus court, on recommence (cas d'un retry)
        if len(new_text) < len(self._last_text):
            self._last_text = ""
            return new_text
        
        # On ne garde que la nouvelle partie
        diff = new_text[len(self._last_text):]
        
        # Met à jour le dernier texte
        self._last_text = new_text
        
        return diff

class MockProgressService:
    """Service de mock pour le streaming et le suivi de la progression."""
    
    def __init__(self):
        self._streaming = False
        self._first_chunk = True
        self._last_newline = False
        self._diff_service = StreamDiffService()
    
    async def update_step(
        self,
        progress_id: str,
        step: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        if details:
            # Début du streaming
            if self._first_chunk:
                print("\n\033[36m=== Start of stream ===\033[0m\n", flush=True)
                self._first_chunk = False
                self._streaming = True
            
            # Obtient uniquement la différence à afficher
            diff = self._diff_service.update(details)
            if diff:  # N'affiche que s'il y a une différence
                print(diff, end="", flush=True)
            
            # Garde en mémoire si on termine par un saut de ligne
            self._last_newline = details.endswith("\n")
        
        elif message:
            # Si on était en train de streamer, on termine le stream
            if self._streaming:
                if not self._last_newline:
                    print()  # Ajoute un saut de ligne si nécessaire
                print("\n\033[36m=== End of stream ===\033[0m\n", flush=True)
                self._streaming = False
                self._first_chunk = True
            
            # Affiche les messages de progression en jaune
            print(f"\033[33m[INFO] {message}\033[0m")

def load_recipe_files(input_dir: str, recipe_slug: str) -> tuple[str, Optional[bytes]]:
    """Load recipe text and image files from input directory."""
    input_path = Path(input_dir)
    
    # Load text content
    text_file = input_path / f"{recipe_slug}.txt"
    if not text_file.exists():
        raise FileNotFoundError(f"Recipe text file not found: {text_file}")
    
    with open(text_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    # Try to load image if it exists
    image_data = None
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        image_file = input_path / f"{recipe_slug}{ext}"
        if image_file.exists():
            with open(image_file, 'rb') as f:
                image_data = f.read()
            break
    
    return text_content, image_data 