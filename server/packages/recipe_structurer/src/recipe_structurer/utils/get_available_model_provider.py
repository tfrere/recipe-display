import os
import logging
from huggingface_hub import model_info, InferenceClient
from dotenv import load_dotenv

# Definition of preferred providers
PREFERRED_PROVIDERS = ["fireworks-ai", "groq", "nebius", "together", "deepinfra", "cohere", "perplexity", "anthropic", "sambanova", "novita"]

# Load environment variables once at the module level
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def prioritize_providers(providers):
    """Prioritize preferred providers, keeping all others."""
    return sorted(providers, key=lambda provider: provider not in PREFERRED_PROVIDERS)

def test_provider(model_name: str, provider: str, verbose: bool = False) -> bool:
    """
    Test if a specific provider is available for a model using InferenceClient
    
    Args:
        model_name: Name of the model
        provider: Provider to test
        verbose: Whether to log detailed information
        
    Returns:
        True if the provider is available, False otherwise
    """
    try:
        # Get HF token from environment
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            if verbose:
                logger.warning("No HF_TOKEN found in environment variables. This will likely cause authentication failures.")
                print("WARNING: HF_TOKEN is missing. Most model providers require valid authentication.")
            # Essayer sans token (pour certains providers qui acceptent des requêtes anonymes)
            return _test_provider_without_token(model_name, provider, verbose)
        
        if verbose:
            logger.info(f"Testing provider {provider} for model {model_name}")
        
        # Initialize the InferenceClient with the specific provider
        try:
            client = InferenceClient(
                model=model_name,
                token=hf_token,
                provider=provider,
                timeout=3  # Increased timeout to allow model loading
            )
                
            try:
                # Use the chat completions method for testing
                response = client.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                
                if verbose:
                    logger.info(f"Provider {provider} is available for {model_name}")
                return True
                
            except Exception as e:
                if verbose:
                    error_message = str(e)
                    logger.warning(f"Error with provider {provider}: {error_message}")
                    
                    # Log specific error types if we can identify them
                    if "status_code=429" in error_message:
                        logger.warning(f"Provider {provider} rate limited. You may need to wait or upgrade your plan.")
                    elif "status_code=401" in error_message or "status_code=403" in error_message:
                        logger.warning(f"Authentication failed for provider {provider}. Your HF_TOKEN may be invalid or expired.")
                        print(f"Authentication error with provider {provider}. Please check your HF_TOKEN.")
                        # Essayer sans token
                        if verbose:
                            logger.info(f"Trying provider {provider} without authentication")
                        return _test_provider_without_token(model_name, provider, verbose)
                    elif "status_code=503" in error_message:
                        logger.warning(f"Provider {provider} service unavailable. Model may be loading or provider is down.")
                    elif "timed out" in error_message.lower():
                        logger.warning(f"Timeout error with provider {provider} - request timed out after 10 seconds")
                return False
        except Exception as auth_error:
            if "401" in str(auth_error) or "Unauthorized" in str(auth_error):
                # En cas d'erreur d'authentification, essayer sans token
                if verbose:
                    logger.warning(f"Authentication error with {provider}: {str(auth_error)}. Your HF_TOKEN may be invalid.")
                    print(f"Authentication error detected. Please verify your HF_TOKEN is valid and has appropriate permissions.")
                return _test_provider_without_token(model_name, provider, verbose)
            else:
                if verbose:
                    logger.warning(f"Error creating client for {provider}: {str(auth_error)}")
                return False
            
    except Exception as e:
        if verbose:
            logger.warning(f"Error in test_provider: {str(e)}")
        return False

def _test_provider_without_token(model_name: str, provider: str, verbose: bool = False) -> bool:
    """
    Essaye de tester un provider sans token d'authentification
    
    Args:
        model_name: Nom du modèle
        provider: Provider à tester
        verbose: Afficher les logs détaillés
        
    Returns:
        True si le provider est disponible, False sinon
    """
    try:
        if verbose:
            logger.info(f"Testing provider {provider} for model {model_name} without authentication")
        
        # Initialize without token
        client = InferenceClient(
            model=model_name,
            provider=provider,
            timeout=3
        )
        
        try:
            # Use the chat completionas method for testing
            response = client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            if verbose:
                logger.info(f"Provider {provider} is available for {model_name} without authentication")
            return True
            
        except Exception as e:
            if verbose:
                logger.warning(f"Error with provider {provider} without authentication: {str(e)}")
            return False
            
    except Exception as e:
        if verbose:
            logger.warning(f"Error in _test_provider_without_token: {str(e)}")
        return False

def get_available_model_provider(model_name, verbose=False):
    """
    Get the first available provider for a given model.
    
    Args:
        model_name: Name of the model on the Hub
        verbose: Whether to log detailed information
        
    Returns:
        First available provider or None if none are available
    """
    try:
        # Get HF token from environment
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            if verbose:
                logger.error("HF_TOKEN not defined in environment")
            raise ValueError("HF_TOKEN not defined in environment")
        
        # Get providers for the model and prioritize them
        info = None
        try:
            # Essayer avec le token
            try:
                if verbose:
                    logger.info(f"Trying to get model info for {model_name} with auth token")
                info = model_info(model_name, token=hf_token, expand="inferenceProviderMapping")
            except Exception as auth_error:
                # Si l'authentification échoue, essayer sans token (pour les modèles publics)
                if "401" in str(auth_error) or "Unauthorized" in str(auth_error):
                    if verbose:
                        logger.warning(f"Authentication failed for {model_name}, trying without token")
                    # Essayer de récupérer les infos sans token
                    try:
                        info = model_info(model_name, expand="inferenceProviderMapping")
                    except Exception as e:
                        if verbose:
                            logger.error(f"Failed to get model info without token: {str(e)}")
                        # Comme dernier recours, retourner la liste des providers par défaut pour tester
                        if verbose:
                            logger.warning(f"Using default providers list as fallback for {model_name}")
                        # Fournir une liste de providers de secours pour tester directement
                        return _test_fallback_providers(model_name, verbose)
                else:
                    # Autre erreur, la relancer
                    raise auth_error
            
            if not info or not hasattr(info, "inference_provider_mapping"):
                if verbose:
                    logger.info(f"No inference providers found for {model_name}")
                # Essayer avec la liste de providers par défaut
                return _test_fallback_providers(model_name, verbose)
            
            providers = list(info.inference_provider_mapping.keys())
            if not providers:
                if verbose:
                    logger.info(f"Empty list of providers for {model_name}")
                # Essayer avec la liste de providers par défaut
                return _test_fallback_providers(model_name, verbose)
                
        except Exception as e:
            if verbose:
                logger.error(f"Error retrieving model info for {model_name}: {str(e)}")
            # Essayer avec la liste de providers par défaut
            return _test_fallback_providers(model_name, verbose)
            
        # Prioritize providers
        prioritized_providers = prioritize_providers(providers)
        
        if verbose:
            logger.info(f"Available providers for {model_name}: {', '.join(providers)}")
            logger.info(f"Prioritized providers: {', '.join(prioritized_providers)}")
        
        # Test each preferred provider first
        failed_providers = []
        for provider in prioritized_providers:
            if verbose:
                logger.info(f"Testing provider {provider} for {model_name}")
            
            try:
                if test_provider(model_name, provider, verbose):
                    if verbose:
                        logger.info(f"Provider {provider} is available for {model_name}")
                    return provider
                else:
                    failed_providers.append(provider)
                    if verbose:
                        logger.warning(f"Provider {provider} test failed for {model_name}")
            except Exception as e:
                failed_providers.append(provider)
                if verbose:
                    logger.error(f"Exception while testing provider {provider} for {model_name}: {str(e)}")
                
        # If all prioritized providers failed, try any remaining providers
        remaining_providers = [p for p in providers if p not in prioritized_providers and p not in failed_providers]
        
        if remaining_providers and verbose:
            logger.info(f"Trying remaining non-prioritized providers: {', '.join(remaining_providers)}")
            
        for provider in remaining_providers:
            if verbose:
                logger.info(f"Testing non-prioritized provider {provider} for {model_name}")
                
            try:
                if test_provider(model_name, provider, verbose):
                    if verbose:
                        logger.info(f"Non-prioritized provider {provider} is available for {model_name}")
                    return provider
            except Exception as e:
                if verbose:
                    logger.error(f"Exception while testing non-prioritized provider {provider}: {str(e)}")
                
        # If we've tried all providers and none worked, log this but don't raise an exception
        if verbose:
            logger.error(f"No available providers for {model_name}. Tried {len(failed_providers + remaining_providers)} providers.")
        return None
        
    except Exception as e:
        if verbose:
            logger.error(f"Error in get_available_model_provider: {str(e)}")
        return None
        
def _test_fallback_providers(model_name, verbose=False):
    """
    Fonction de secours qui teste une liste de providers communs sans passer par l'API
    
    Args:
        model_name: Nom du modèle
        verbose: Afficher les logs détaillés
    
    Returns:
        Le premier provider disponible ou None
    """
    # Liste de providers à tester en direct
    default_providers = ["huggingface", "fireworks-ai", "groq", "nebius", "together", "deepinfra", "cohere", "perplexity", "anthropic", "sambanova", "novita", "openai"]
    
    if verbose:
        logger.warning(f"Using fallback providers list for {model_name}: {', '.join(default_providers)}")
    
    # Tester chaque provider directement
    for provider in default_providers:
        if verbose:
            logger.info(f"Testing fallback provider {provider} for {model_name}")
        try:
            if test_provider(model_name, provider, verbose):
                if verbose:
                    logger.info(f"FALLBACK: Provider {provider} is available for {model_name}")
                return provider
        except Exception as e:
            if verbose:
                logger.warning(f"FALLBACK: Error testing provider {provider} for {model_name}: {str(e)}")
    
    return None