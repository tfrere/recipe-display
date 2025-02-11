"""Custom Deepseek model with streaming support"""
import json
from typing import AsyncIterator, Any
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.settings import ModelSettings
from openai import AsyncOpenAI

from ..models.recipe import LLMRecipe, LLMRecipeGraph

class StreamingDeepseekModel(OpenAIModel):
    """Custom model that combines streaming, retries and Deepseek"""
    
    def __init__(
        self, 
        api_key: str, 
        model_name: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        # Passer uniquement les paramètres de base au parent
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url="https://api.deepseek.com/v1"
        )
        
        # Stocker les paramètres de génération
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.additional_params = kwargs
        
        # Initialiser le client OpenAI
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        self._current_step = ""
        self._retry_count = 0
        self._max_retries = 5
        
    async def stream_content(self, messages: list[dict[str, str]]) -> tuple[bool, str]:
        """Stream content from the model and return final response"""
        print(f"\n📡 Sending request to Deepseek API...")
        print(f"Request payload size: {len(str(messages))} characters")
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **self.additional_params
            )
            
            content_received = False
            final_response = ""
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    if not content_received:
                        print("📥 Started receiving content...")
                        content_received = True
                    
                    content = chunk.choices[0].delta.content
                    final_response += content
                    
                    # Update current step for progress display
                    if '"metadata":' in content:
                        self._current_step = "Metadata"
                    elif '"ingredients":' in content:
                        self._current_step = "Ingredients"
                    elif '"steps":' in content:
                        self._current_step = "Steps"
                    elif '"final_state":' in content:
                        self._current_step = "Final State"
                    
                    # Print progress indicator
                    if self._current_step:
                        print(f"\r🔄 Generating {self._current_step}... ", end="", flush=True)
                    
                    print(content, end="", flush=True)
            
            if not content_received:
                print("⚠️  No content received from API")
                return False, ""
            else:
                print("\n📥 Finished receiving content")
                return True, final_response
                
        except Exception as e:
            print(f"\n❌ API Error: {str(e)}")
            raise
            
    def _try_parse_json(self, text: str) -> tuple[bool, Any]:
        """Try to parse text as JSON and print if valid"""
        try:
            # Remove markdown code block if present
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
                text = text.replace("```", "", 1)
            elif text.startswith("```"):
                text = text.replace("```", "", 2)  # Remove both opening and closing ```
            
            # Remove any text before the first {
            json_start = text.find("{")
            if json_start == -1:
                print("⚠️  No JSON object found in response")
                print(f"Text received: {text[:100]}...")
                return False, None
            
            json_text = text[json_start:]
            # Find the last }
            json_end = json_text.rfind("}")
            if json_end == -1:
                print("⚠️  No closing brace found in JSON")
                return False, None
                
            json_text = json_text[:json_end + 1]
            
            try:
                parsed = json.loads(json_text)
                return True, parsed
            except json.JSONDecodeError as e:
                print(f"\n⚠️  JSON parsing error: {str(e)}")
                print(f"Error location: around character {e.pos}")
                print(f"Problem section: {json_text[max(0, e.pos-50):min(len(json_text), e.pos+50)]}")
                return False, None
            
        except Exception as e:
            print(f"\n⚠️  Unexpected error while parsing JSON: {str(e)}")
            print(f"Full text received: {text}")
            return False, None
            
    def _enhance_prompt_with_error(self, prompt: str, error: str) -> str:
        """Enhance the prompt with error feedback"""
        return f"""Previous attempt failed with these validation errors:
{error}

Please fix ALL validation errors while keeping the same structure.
Make sure to follow the schema EXACTLY.

Here is the original prompt again:
{prompt}"""

    async def complete(self, messages: list[dict[str, str]], settings: ModelSettings | None = None, validation_model: type = LLMRecipe) -> Any:
        """Override complete to add streaming support with retries"""
        if settings and isinstance(settings, dict) and settings.get("stream", False):
            # Reset retry count for new request
            self._retry_count = 0
            
            while self._retry_count < self._max_retries:
                try:
                    # Stream the response and get final content
                    success, final_response = await self.stream_content(messages)
                    
                    if not success:
                        raise ValueError("Empty response from API - aborting")
                    
                    # Try to parse and validate
                    is_valid_json, parsed_json = self._try_parse_json(final_response)
                    if is_valid_json:
                        try:
                            # Try to validate with appropriate model
                            recipe = validation_model.model_validate(parsed_json)
                            print("\n\n✅ Recipe structure generated and validated successfully!")
                            return recipe
                        except Exception as e:
                            print(f"\n\n⚠️  Validation failed, retrying... ({self._retry_count + 1}/{self._max_retries})")
                            print(f"Error: {str(e)}")
                            
                            if self._retry_count < self._max_retries - 1:
                                # Update messages with error feedback
                                messages = [
                                    messages[0],  # Keep system message
                                    {
                                        "role": "user",
                                        "content": self._enhance_prompt_with_error(messages[1]["content"], str(e))
                                    }
                                ]
                                self._retry_count += 1
                                continue
                            else:
                                raise
                    else:
                        print("\n\n⚠️  Invalid JSON generated")
                        if self._retry_count < self._max_retries - 1:
                            self._retry_count += 1
                            continue
                        else:
                            raise ValueError("Failed to generate valid JSON after all retries")
                
                except ValueError as e:
                    if "Empty response from API" in str(e):
                        print("\n❌ Aborting due to empty API response")
                        raise
                    raise
                
            raise ValueError(f"Failed to generate valid recipe after {self._max_retries} attempts")
        else:
            return await super().complete(messages, settings) 