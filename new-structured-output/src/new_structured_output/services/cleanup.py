"""Service for cleaning up recipe text"""
from typing import AsyncIterator
from ..providers.deepseek_model import StreamingDeepseekModel
from ..prompts.cleanup import cleanup_prompt

async def cleanup_recipe(model: StreamingDeepseekModel, recipe_text: str) -> str:
    """Clean up the recipe text format"""
    print("\n🧹 Cleaning recipe format...")
    print("⌛ This may take a minute...\n")
    
    messages = [
        {
            "role": "system",
            "content": cleanup_prompt
        },
        {
            "role": "user",
            "content": recipe_text
        }
    ]
    
    success, cleaned_text = await model.stream_content(messages)
    
    if not success:
        raise ValueError("Failed to clean up recipe - empty response from API")
        
    print("\n✨ Recipe cleanup completed!")
    return cleaned_text 