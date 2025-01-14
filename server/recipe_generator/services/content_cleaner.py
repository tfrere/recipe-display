from typing import Optional, Callable, Awaitable
from openai import AsyncOpenAI
from ..models.web_content import WebContent
from ..prompts.cleanup_recipe import format_cleanup_recipe_prompt
from ..utils.error_utils import save_error_to_file
from ..config import load_config
from ..models.text_content import TextContent

class ContentCleaner:
    """Service for cleaning and organizing recipe content."""
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
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
        
        print("\nSending prompt to OpenAI")  # Debug
        content = ""
        total_chunks = 0
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.config["cleanup_model"],
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    }
                ],
                temperature=self.config["temperature"],
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    # Get the new content
                    new_content = chunk.choices[0].delta.content
                    total_chunks += 1
                    
                    # Add to accumulated content
                    content += new_content
                    
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
    ) -> TextContent:
        """Clean up and organize recipe text content."""
        print("\nStarting text content cleaning")  # Debug
        
        # Format prompt with empty image list since we don't have images
        prompt = format_cleanup_recipe_prompt(
            content=text,
            image_urls=[]
        )
        
        print("\nSending prompt to OpenAI")  # Debug
        content = ""
        total_chunks = 0
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.config["cleanup_model"],
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    }
                ],
                temperature=self.config["temperature"],
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    # Get the new content
                    new_content = chunk.choices[0].delta.content
                    total_chunks += 1
                    
                    # Add to accumulated content
                    content += new_content
                    
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
                        "content": text
                    }
                }
                save_error_to_file(error_data)
                raise ValueError(content)
            
            # Create and return TextContent - no image handling here as it's done separately
            return TextContent(
                main_content=content,
                selected_image_url=""  # Always empty as images are handled separately
            )
            
        except Exception as e:
            print(f"[ERROR] Failed to clean text content: {str(e)}")
            raise