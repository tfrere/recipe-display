"""Custom HuggingFace model with streaming support"""
import json
import os
from typing import AsyncIterator, Any, Dict, List
from huggingface_hub import InferenceClient, model_info
from pydantic_ai.settings import ModelSettings

from ..models.recipe import LLMRecipe, LLMRecipeGraph
from ..utils.get_available_model_provider import get_available_model_provider, test_provider, prioritize_providers

class StreamingHuggingFaceModel:
    """Custom model that combines streaming, retries and HuggingFace Inference API"""
    
    def __init__(self, api_key: str, model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"):
        self.model_name = model_name
        self.api_key = api_key
        
        if not api_key:
            raise ValueError("HF_TOKEN is not set in environment variables")
        
        # Test providers for this model and get the available provider
        provider = self._get_available_provider()
        if not provider:
            raise ValueError(f"No available provider found for model {model_name}")
        
        print(f"Using provider: {provider} for model {model_name}")
        
        self.client = InferenceClient(
            token=api_key,
            provider=provider,
        )
        self._current_step = ""
        self._retry_count = 0
        self._max_retries = 5
    
    def _get_available_provider(self) -> str:
        """Test and get the first available provider for the model"""
        provider = get_available_model_provider(self.model_name, verbose=True)
        return provider
        
    def _get_next_available_provider(self) -> str:
        """Find the next available provider, excluding the current one"""
        current_provider = getattr(self.client, "provider", None)
        
        # Get all available providers for the model
        try:
            info = model_info(self.model_name, token=self.api_key, expand="inferenceProviderMapping")
            if not hasattr(info, "inference_provider_mapping"):
                return None
                
            providers = list(info.inference_provider_mapping.keys())
            # Exclure le provider actuel
            providers = [p for p in providers if p != current_provider]
            
            # Prioritiser les providers
            prioritized_providers = prioritize_providers(providers)
            
            print(f"Looking for alternative providers, candidates: {', '.join(prioritized_providers)}")
            
            # Tester chaque provider
            for provider in prioritized_providers:
                try:
                    if test_provider(self.model_name, provider, verbose=True):
                        return provider
                except Exception as e:
                    print(f"Provider {provider} test failed: {str(e)}")
                    continue
            
            # Si aucun provider disponible dans la liste normale, essayer la liste de secours
            from ..utils.get_available_model_provider import _test_fallback_providers
            return _test_fallback_providers(self.model_name, verbose=True)
            
        except Exception as e:
            print(f"Error finding alternative provider: {str(e)}")
            return None
        
    async def stream_content(self, messages: list[dict[str, str]]) -> tuple[bool, str]:
        """Stream content from the model and return final response"""
        print(f"\n📡 Sending request to HuggingFace Inference API...")
        
        try:
            # Calculer la taille du prompt
            print(f"📊 Prompt details:")
            for i, msg in enumerate(messages):
                print(f"- Message {i+1} ({msg['role']}): {len(msg['content'])} chars")
            
            # Convert OpenAI format to HuggingFace chat format
            hf_messages = []
            for msg in messages:
                hf_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            stream = self.client.chat_completion(
                model=self.model_name,
                messages=hf_messages,
                stream=True,
                max_tokens=8192,
                temperature=0.7,
                top_p=0.95,
            )
            
            content_received = False
            final_response = ""
            
            # Must be used in a sync context for HuggingFace's client
            for response in stream:
                if response.choices and response.choices[0].delta.content:
                    if not content_received:
                        print("📥 Started receiving content...")
                        content_received = True
                    
                    content = response.choices[0].delta.content
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
                print("\n⚠️  No content received from API")
                print("💡 This might be because:")
                print("- The prompt is too long")
                print("- The API timed out")
                print("- There was a connection error")
                return False, ""
            else:
                print("\n📥 Finished receiving content")
                return True, final_response
                
        except Exception as e:
            error_str = str(e)
            # Vérifier si c'est une erreur de rate limit ou timeout
            if ("rate_limit_exceeded" in error_str or "status_code=429" in error_str or 
                "timed out" in error_str.lower()):
                print(f"\n⚠️ Provider {getattr(self.client, 'provider', 'unknown')} rate limited or timed out. Trying another provider...")
                
                # Essayer de changer de provider
                new_provider = self._get_next_available_provider()
                if new_provider:
                    print(f"✅ Switching to provider: {new_provider}")
                    self.client = InferenceClient(
                        token=self.api_key,
                        provider=new_provider,
                    )
                    # Réessayer avec le nouveau provider
                    return await self.stream_content(messages)
                else:
                    print("❌ No alternative providers available")
            
            # Si ce n'est pas une erreur de rate limit ou si aucun autre provider n'est disponible
            print(f"\n❌ API Error: {error_str}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response}")
            raise
    
    def _convert_to_hf_format(self, messages: list[dict[str, str]]) -> str:
        """Convert OpenAI-style messages to HuggingFace prompt format"""
        prompt = ""
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            # Format based on Qwen's expected format
            if role == "system":
                prompt += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        
        # Add the final assistant token to indicate where the model should generate
        prompt += "<|im_start|>assistant\n"
        
        return prompt
            
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
            # For non-streaming requests, use a single request
            # Convert to OpenAI format to HuggingFace chat format
            hf_messages = []
            for msg in messages:
                hf_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            response = self.client.chat_completion(
                model=self.model_name,
                messages=hf_messages,
                max_tokens=8192,
                temperature=0.7,
                top_p=0.95,
            )
            
            content = response.choices[0].message.content
            parsed_json = json.loads(content)
            return validation_model.model_validate(parsed_json) 