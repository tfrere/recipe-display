"""Service for generating recipe preparation graph"""
from ..providers.deepseek_model import StreamingDeepseekModel
from ..models.recipe import LLMRecipeBase, LLMRecipeGraph
from ..prompts.graph import graph_prompt

async def generate_graph(model: StreamingDeepseekModel, recipe_base: LLMRecipeBase, cleaned_text: str) -> LLMRecipeGraph:
    """Generate recipe graph (steps and final state)"""
    print("\n📊 Generating recipe preparation graph...")
    graph_messages = [
        {
            "role": "system",
            "content": graph_prompt.format(recipe_base=recipe_base.model_dump_json(indent=2))
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