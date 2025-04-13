"""Service for generating recipe preparation graph"""
from ..providers.deepseek_model import StreamingDeepseekModel
from ..models.recipe import LLMRecipeBase, LLMRecipeGraph
from ..prompts.graph import graph_prompt

async def generate_graph(model: StreamingDeepseekModel, recipe_base: LLMRecipeBase, cleaned_text: str) -> LLMRecipeGraph:
    """Generate recipe graph (steps and final state)"""
    print("\n📊 Generating recipe preparation graph...")
    
    # Format prompt with recipe base
    formatted_prompt = graph_prompt.format(recipe_base=recipe_base.model_dump_json(indent=2))
    print(f"\n📝 Recipe base size in prompt: {len(recipe_base.model_dump_json(indent=2))} chars")
    
    graph_messages = [
        {
            "role": "system",
            "content": formatted_prompt
        },
        {
            "role": "user",
            "content": cleaned_text
        }
    ]
    
    # Le modèle va déjà parser et valider la réponse
    return await model.complete(
        messages=graph_messages,
        settings={"stream": True},
        validation_model=LLMRecipeGraph
    ) 