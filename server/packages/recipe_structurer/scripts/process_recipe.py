"""Process a recipe text file into structured JSON"""
import asyncio
import json
import os
import sys
import argparse
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

from recipe_structurer.generator import generate_recipe
from recipe_scraper.recipe_enricher import RecipeEnricher

def count_tokens(text: str) -> int:
    """Rough estimation of token count (4 chars = 1 token)"""
    return len(text) // 4

def ensure_dir(path: Path) -> None:
    """Ensure a directory exists, create it if it doesn't"""
    path.mkdir(parents=True, exist_ok=True)

async def process_recipe_file(
    input_file: Path,
    provider: Literal["deepseek", "mistral"] = "mistral",
    intermediate_dir: Path | None = None,
    output_dir: Path | None = None
) -> None:
    """
    Process a single recipe file
    
    Args:
        input_file: Path to the input recipe text file
        provider: LLM provider to use
        intermediate_dir: Directory for intermediate files (default: ../intermediate relative to input file)
        output_dir: Directory for final output (default: ../output relative to input file)
    """
    print(f"\n🔄 Processing recipe: {input_file.name}")
    print(f"Using {provider} model")
    
    # Create slug from filename
    slug = input_file.stem
    
    # Read input file
    with open(input_file, "r") as f:
        recipe_text = f.read()
    
    print(f"\n📊 Input statistics:")
    print(f"- Characters: {len(recipe_text)}")
    print(f"- Estimated tokens: {count_tokens(recipe_text)}")
    print(f"- Lines: {len(recipe_text.splitlines())}")
        
    # Setup output directories (default: parent of input file)
    base_dir = input_file.parent.parent  # Remonter d'un niveau
    intermediate_dir = intermediate_dir or (base_dir / "intermediate")
    output_dir = output_dir or (base_dir / "output")
    
    # Ensure directories exist
    ensure_dir(intermediate_dir)
    ensure_dir(output_dir)
    
    try:
        # Step 1: Generate and save cleaned text
        print("\n🧹 Step 1: Cleaning recipe format...")
        cleaned_text, recipe_base, recipe_graph = await generate_recipe(
            recipe_text,
            provider=provider
        )
        
        # Save cleaned text immediately
        cleaned_file = intermediate_dir / f"{slug}_cleaned.txt"
        with open(cleaned_file, "w") as f:
            f.write(cleaned_text)
        print(f"📝 Cleaned text saved to: {cleaned_file}")
        
        # Step 2: Save base recipe structure
        print("\n📊 Step 2: Saving base recipe structure...")
        base_file = intermediate_dir / f"{slug}_base.json"
        with open(base_file, "w") as f:
            f.write(recipe_base.model_dump_json(indent=2))
        print(f"💾 Base structure saved to: {base_file}")
        
        # Step 3: Save graph structure
        print("\n🔄 Step 3: Saving recipe graph...")
        graph_file = intermediate_dir / f"{slug}_graph.json"
        with open(graph_file, "w") as f:
            f.write(recipe_graph.model_dump_json(indent=2))
        print(f"💾 Graph structure saved to: {graph_file}")
        
        # Step 4: Combine and save final recipe
        print("\n✨ Step 4: Generating final recipe...")
        final_recipe = {
            "metadata": recipe_base.metadata.model_dump(),
            "ingredients": [ing.model_dump() for ing in recipe_base.ingredients],
            "tools": recipe_base.tools,
            "steps": [step.model_dump() for step in recipe_graph.steps],
            "final_state": recipe_graph.final_state.model_dump()
        }
        
        # Step 5: Enrich recipe with diet, season, and time information
        print("\n🔍 Step 5: Enriching recipe with additional metadata...")
        enricher = RecipeEnricher()
        final_recipe = enricher.enrich_recipe(final_recipe)
        print(f"✅ Recipe enriched with totalTime: {final_recipe.get('metadata', {}).get('totalTime')} minutes")
        print(f"✅ Recipe enriched with totalCookingTime: {final_recipe.get('metadata', {}).get('totalCookingTime')} minutes")
        
        final_file = output_dir / f"{slug}.json"
        with open(final_file, "w") as f:
            json.dump(final_recipe, f, indent=2)
        print(f"✅ Final recipe saved to: {final_file}")
        
        # Print final statistics
        print(f"\n📊 Output statistics:")
        print(f"- Ingredients: {len(recipe_base.ingredients)}")
        print(f"- Steps: {len(recipe_graph.steps)}")
        print(f"- Tools: {len(recipe_base.tools)}")
        
    except Exception as e:
        print(f"\n❌ Error processing recipe: {str(e)}")
        if hasattr(e, '__cause__'):
            print(f"Caused by: {str(e.__cause__)}")
        raise

async def async_main(args: argparse.Namespace):
    """Process recipe file"""
    # Load environment variables
    load_dotenv()
    
    # Get input file
    input_file = Path(args.input_file)
    
    # Verify file exists
    if not input_file.exists():
        print(f"❌ Error: File not found: {input_file}")
        sys.exit(1)
        
    # Verify it's a .txt file
    if input_file.suffix != ".txt":
        print(f"❌ Error: File must be a .txt file: {input_file}")
        sys.exit(1)
        
    # Convert output paths if provided
    intermediate_dir = Path(args.intermediate_dir) if args.intermediate_dir else None
    output_dir = Path(args.output_dir) if args.output_dir else None
        
    await process_recipe_file(
        input_file, 
        args.provider,
        intermediate_dir=intermediate_dir,
        output_dir=output_dir
    )

def main():
    """Entry point for the script"""
    parser = argparse.ArgumentParser(
        description="Process a recipe text file into structured JSON format using LLMs"
    )
    parser.add_argument(
        "input_file",
        help="Path to the recipe text file to process"
    )
    parser.add_argument(
        "--provider",
        choices=["deepseek", "mistral", "huggingface"],
        default="huggingface",
        help="LLM provider to use (default: mistral)"
    )
    parser.add_argument(
        "--intermediate-dir",
        help="Directory for intermediate files (default: ../intermediate relative to input file)"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for final output (default: ../output relative to input file)"
    )
    
    args = parser.parse_args()
    asyncio.run(async_main(args))

if __name__ == "__main__":
    main() 