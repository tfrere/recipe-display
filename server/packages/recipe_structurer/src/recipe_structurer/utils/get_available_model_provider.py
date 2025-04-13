import os
import logging
import json
from huggingface_hub import model_info, InferenceClient
from dotenv import load_dotenv



# Definition of preferred providers, used in get_available_model_provider.py
# PREFERRED_PROVIDERS = ["sambanova", "novita"]
PREFERRED_PROVIDERS = ["fireworks-ai", "sambanova", "novita"]

# Default models to evaluate for evaluation
DEFAULT_EVALUATION_MODELS = [
    "Qwen/QwQ-32B",
    "Qwen/Qwen2.5-72B-Instruct",
    "Qwen/Qwen2.5-32B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "meta-llama/Llama-3.3-70B-Instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
    "mistralai/Mistral-Small-24B-Instruct-2501",
]

# Modèles alternatifs à utiliser si le modèle par défaut n'est pas disponible
ALTERNATIVE_BENCHMARK_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "mistralai/Mistral-Small-24B-Instruct-2501",
    # Modèles open-source qui peuvent fonctionner sans authentification
    "HuggingFaceH4/zephyr-7b-beta",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "microsoft/phi-2",
]

# Required model for create_bench_config_file.py (only one default model)
DEFAULT_BENCHMARK_MODEL = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"


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
        load_dotenv()
        
        # Get HF token from environment
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            if verbose:
                logger.warning("No HF_TOKEN found in environment variables. This will likely cause authentication failures.")
                print("WARNING: HF_TOKEN is missing. Most model providers require valid authentication.")
            # Essayer sans token (pour certains providers qui acceptent des requêtes anonymes)
            return _test_provider_without_token(model_name, provider, verbose)
        
        # Get HF organization from environment
        hf_organization = os.environ.get("HF_ORGANIZATION")
        if not hf_organization:
            if verbose:
                logger.warning("HF_ORGANIZATION not defined in environment")
        
        if verbose:
            logger.info(f"Testing provider {provider} for model {model_name}")
        
        # Initialize the InferenceClient with the specific provider
        try:
            client = InferenceClient(
                model=model_name,
                token=hf_token,
                provider=provider,
                # bill_to=hf_organization if hf_organization else None,
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
    default_providers = ["huggingface", "sambanova", "novita", "fireworks-ai", "together", "openai", "anthropic"]
    
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

def test_models(verbose=True):
    """
    Test le modèle par défaut et les modèles alternatifs, puis retourne un résumé des résultats.
    
    Args:
        verbose: Afficher les logs détaillés
        
    Returns:
        Un dictionnaire avec les résultats des tests
    """
    results = {
        "default_model": None,
        "working_model": None,
        "provider": None,
        "all_models": {},
        "available_models": [],
        "unavailable_models": []
    }
    
    print("\n===== Checking HuggingFace Authentication =====")
    # Obtenez le jeton HF
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        print("✅ HF_TOKEN is available")
        
        # Vérifier si le token a un format valide (vérification simple)
        if not hf_token.startswith("hf_"):
            print("⚠️ WARNING: Your HF_TOKEN does not start with 'hf_' which is unusual. Please verify its format.")
        
        # Ne montrer aucun caractère du token, juste indiquer sa présence
        masked_token = "••••••••••"
        
        # Vérifier la validité du token en testant directement l'API d'inférence
        import requests
        try:
            # Test avec un modèle public simple (gpt2)
            test_model = "gpt2"
            api_url = f"https://api-inference.huggingface.co/models/{test_model}"
            
            print(f"Testing token with inference API on public model {test_model}...")
            
            headers = {"Authorization": f"Bearer {hf_token}"}
            payload = {"inputs": "Hello, how are you?"}
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code in [200, 503]:  # 503 = modèle en cours de chargement, mais le token est accepté
                print(f"✅ HF_TOKEN validated - Token accepted by the inference API! Status: {response.status_code}")
                if response.status_code == 503:
                    print("ℹ️ Model is loading, but token is valid")
                
                # Si le token est valide pour l'API d'inférence, vérifions également si nous pouvons obtenir
                # des informations sur l'utilisateur (mais ce n'est pas bloquant si ça échoue)
                try:
                    whoami_response = requests.get(
                        "https://huggingface.co/api/whoami",
                        headers={"Authorization": f"Bearer {hf_token}"}
                    )
                    
                    if whoami_response.status_code == 200:
                        user_info = whoami_response.json()
                        print(f"✅ Additional info - Authenticated as: {user_info.get('name', 'Unknown user')}")
                        
                        # Vérifier si l'utilisateur a accès à des modèles payants
                        if user_info.get('canPay', False):
                            print("✅ Your account has payment methods configured - you may have access to premium models")
                        else:
                            print("ℹ️ Your account does not have payment methods configured - access to premium models may be limited")
                except Exception:
                    # Ignorer les erreurs lors de la récupération des infos utilisateur
                    pass
            else:
                print(f"❌ HF_TOKEN validation failed with status code: {response.status_code}")
                error_message = "Unknown error"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_message = error_data["error"]
                        print(f"❌ Error message: {error_message}")
                except:
                    print(f"❌ Error message: {response.text}")
                
                print("⚠️ Most model providers will not work with invalid credentials")
                
                # Test alternatif avec l'endpoint status
                try:
                    print("Attempting alternative validation with status endpoint...")
                    status_url = "https://api-inference.huggingface.co/status"
                    status_response = requests.get(status_url, headers=headers, timeout=10)
                    
                    if status_response.status_code == 200:
                        print("✅ Token can access the status endpoint. This is partially good news.")
                    else:
                        print(f"❌ Status endpoint test also failed: {status_response.status_code}")
                except Exception as e:
                    print(f"❌ Alternative validation also failed: {str(e)}")
        except Exception as e:
            print(f"❌ Error validating HF_TOKEN with inference API: {str(e)}")
    else:
        print("❌ HF_TOKEN is missing - authentication to HuggingFace API will fail")
        print("⚠️ Most models and providers require authentication")

    # Obtenez l'organisation HF
    hf_organization = os.environ.get("HF_ORGANIZATION")
    if hf_organization:
        print(f"✅ HF_ORGANIZATION is available: {hf_organization}")
    else:
        print("ℹ️ HF_ORGANIZATION is not set")
    
    if verbose:
        print(f"\n===== Testing main default model: {DEFAULT_BENCHMARK_MODEL} =====")
        
    # Test du modèle par défaut
    provider = get_available_model_provider(DEFAULT_BENCHMARK_MODEL, verbose=verbose)
    
    if provider:
        if verbose:
            print(f"\n✅ SUCCESS: Found provider for default model {DEFAULT_BENCHMARK_MODEL}: {provider}")
        results["default_model"] = DEFAULT_BENCHMARK_MODEL
        results["working_model"] = DEFAULT_BENCHMARK_MODEL
        results["provider"] = provider
    else:
        if verbose:
            print(f"\n❌ DEFAULT MODEL FAILED: No provider found for {DEFAULT_BENCHMARK_MODEL}")
            print("Trying alternative models...")
        
        # Essayer les modèles alternatifs
        for alt_model in ALTERNATIVE_BENCHMARK_MODELS:
            if verbose:
                print(f"\nTrying alternative model: {alt_model}")
            alt_provider = get_available_model_provider(alt_model, verbose=verbose)
            if alt_provider:
                if verbose:
                    print(f"\n✅ SUCCESS: Found provider for alternative model {alt_model}: {alt_provider}")
                results["working_model"] = alt_model
                results["provider"] = alt_provider
                break
            elif verbose:
                print(f"❌ Failed to find provider for alternative model: {alt_model}")
        else:
            if verbose:
                print("\n❌ ALL MODELS FAILED: No provider found for any model")
                print("\n⚠️ This is likely due to authentication issues with your HF_TOKEN")
                print("⚠️ Please check your token or try using models that don't require authentication")
    
    # Tester tous les modèles pour avoir une vue d'ensemble
    models = [
        "Qwen/QwQ-32B",
        "Qwen/Qwen2.5-72B-Instruct",
        "Qwen/Qwen2.5-32B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        "meta-llama/Llama-3.3-70B-Instruct",
        "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        "mistralai/Mistral-Small-24B-Instruct-2501",
    ]

    if verbose:
        print("\n===== Testing all available models =====")

    for model in models:
        provider = get_available_model_provider(model, verbose)
        results["all_models"][model] = provider
        if provider:
            results["available_models"].append((model, provider))
        else:
            results["unavailable_models"].append(model)
    
    if verbose:
        print("\n===== Results Summary =====")
        if results["available_models"]:
            print("Models with available providers:")
            for model, provider in results["available_models"]:
                print(f"✅ Model: {model}, Provider: {provider}")
        else:
            print("❌ No models with available providers found")
            print("⚠️ Please check your HF_TOKEN and permissions")
            
        if results["unavailable_models"]:
            print("\nModels with no available providers:")
            for model in results["unavailable_models"]:
                print(f"❌ {model}")
        
        print(f"\nTotal Available Models: {len(results['available_models'])}")
        print(f"Total Unavailable Models: {len(results['unavailable_models'])}")
    
    return results
        
if __name__ == "__main__":
    # Exécuter le test si le script est lancé directement
    test_results = test_models(verbose=True)