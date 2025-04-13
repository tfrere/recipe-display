"""Service for cleaning up recipe text"""
from typing import AsyncIterator, List, Optional
from ..providers.deepseek_model import StreamingDeepseekModel
from ..providers.mistral_model import StreamingMistralModel
from ..prompts.cleanup import cleanup_prompt
from ..exceptions import RecipeRejectedError

async def cleanup_recipe(model: StreamingDeepseekModel | StreamingMistralModel, recipe_text: str, image_urls: Optional[List[str]] = None) -> str:
    """Clean up the recipe text format"""
    print("\n[DEBUG] cleanup_recipe called")
    print(f"[DEBUG] Model type: {type(model)}")
    print(f"[DEBUG] Recipe text length: {len(recipe_text)}")
    print(f"[DEBUG] Recipe text preview: {recipe_text[:200]}...")
    
    # Initialiser image_urls comme une liste vide s'il est None
    if image_urls is None:
        image_urls = []
    
    print(f"[DEBUG] Number of images: {len(image_urls)}")
    
    # Format images section
    images_section = "\nAVAILABLE IMAGES:\n"
    for i, url in enumerate(image_urls, 1):
        images_section += f"{i}. {url}\n"
    
    messages = [
        {
            "role": "system",
            "content": cleanup_prompt
        },
        {
            "role": "user",
            "content": recipe_text + images_section
        }
    ]
    
    print("[DEBUG] Calling LLM with cleanup prompt...")
    success, cleaned_text = await model.stream_content(messages)
    
    if not success:
        print("[ERROR] LLM returned empty response")
        raise ValueError("Failed to clean up recipe - empty response from API")
    
    print(f"[DEBUG] LLM response length: {len(cleaned_text)}")
    print(f"[DEBUG] LLM response preview: {cleaned_text[:200]}...")
    
    # Check if the response is a rejection
    if cleaned_text.strip().startswith("REJECT:"):
        rejection_reason = cleaned_text.replace("REJECT:", "").strip()
        print(f"[INFO] Recipe was rejected: {rejection_reason}")
        raise RecipeRejectedError(rejection_reason)
    
    print("[DEBUG] Recipe cleanup completed!")
    return cleaned_text 