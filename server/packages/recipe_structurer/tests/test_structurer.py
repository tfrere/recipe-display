"""Tests for Recipe Structurer (Instructor + DeepSeek/OpenRouter)"""

import asyncio
import os
import pytest
from dotenv import load_dotenv

from recipe_structurer import RecipeStructurer, Recipe
from recipe_structurer.generator import RecipeGenerator
from recipe_structurer.models.recipe import Metadata, Ingredient, Step
from recipe_structurer.exceptions import RecipeRejectedError


# =============================================================================
# Test Data
# =============================================================================

SAMPLE_RECIPE_SIMPLE = """
Classic Chocolate Cake

A rich and moist chocolate cake that serves 8 people.

Ingredients:
- 200g flour
- 50g cocoa powder
- 200g sugar
- 2 eggs
- 100ml milk
- 100g butter
- 1 tsp baking powder

Instructions:
1. Preheat oven to 180°C
2. Mix dry ingredients (flour, cocoa powder, sugar, baking powder)
3. Add wet ingredients (eggs, milk, melted butter) and mix well
4. Pour into cake tin
5. Bake for 30 minutes
6. Cool before serving
"""

SAMPLE_RECIPE_FRENCH = """
Blanquette de veau
Philippe Etchebest

1 kg de veau (épaule, collier)
3 L d'eau
2 branches de thym frais
4 carottes
2 oignons
60 g de beurre
60 g de farine
20 cl de crème liquide
Sel, poivre

Préparation :
Dans un faitout, blanchir le veau départ eau froide.
Ajouter les légumes, thym, sel et poivre.
Laisser cuire 1h30 à feu doux.
Faire un roux avec beurre et farine.
Incorporer le bouillon pour lier la sauce.
Ajouter la crème fouettée.
"""

SAMPLE_RECIPE_WITH_SUBRECIPES = """
Beef Wellington

Serves 4
Prep: 45 min
Cook: 30 min

Ingredients:
- 800g beef tenderloin
- 200g mushrooms
- 150g pâté
- 400g puff pastry
- 2 egg yolks
- Salt, pepper
- Thyme

For the Duxelles:
1. Finely chop mushrooms
2. Sauté until dry
3. Season and let cool

For the Wellington:
1. Sear the beef on all sides
2. Spread pâté on plastic wrap
3. Add duxelles on top
4. Roll beef in the mixture
5. Wrap in pastry
6. Brush with egg yolk
7. Bake at 200°C for 25 minutes
"""

SAMPLE_LOGIN_PAGE = """
<html>
<body>
    <h1>Login to access recipes</h1>
    <form action="/login" method="post">
        <input type="text" name="username">
        <input type="password" name="password">
        <button type="submit">Login</button>
    </form>
</body>
</html>
"""

SAMPLE_NOISY_WEBPAGE = """
Skip to content
Menu
Home | About | Contact | Newsletter

ADVERTISEMENT

The Best Chocolate Chip Cookies Ever!
By Jane Doe | Updated March 2024

Share on Facebook | Tweet | Pin it!

Jump to Recipe | Print Recipe

These are THE BEST chocolate chip cookies you'll ever make! Crispy edges, chewy centers...

[Read more about our cookie journey...]

★★★★★ 4.8 from 1,234 reviews

Prep Time: 15 minutes
Cook Time: 12 minutes
Total Time: 27 minutes
Servings: 24 cookies

EQUIPMENT NEEDED:
- Stand mixer
- Baking sheets

INGREDIENTS:
- 2¼ cups all-purpose flour
- 1 tsp baking soda
- 1 tsp salt
- 1 cup butter, softened
- ¾ cup sugar
- ¾ cup brown sugar
- 2 eggs
- 1 tsp vanilla
- 2 cups chocolate chips

INSTRUCTIONS:
1. Preheat oven to 375°F
2. Mix flour, baking soda, salt
3. Beat butter and sugars until creamy
4. Add eggs and vanilla
5. Gradually add flour mixture
6. Stir in chips
7. Drop onto baking sheets
8. Bake 9-11 minutes

NUTRITION per cookie: 150 cal, 8g fat...

Related Recipes:
- Peanut Butter Cookies
- Oatmeal Raisin Cookies

Comments (847):
User1: Amazing recipe!
User2: Made these for my kids...
[Load more comments]

Footer | Privacy | Terms
© 2024 Cookie Blog
"""


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def load_env():
    """Load environment variables"""
    load_dotenv()
    load_dotenv('../../.env')


@pytest.fixture(scope="module")
def generator(load_env):
    """Create a generator instance"""
    # Check for API key
    if os.getenv("OPENROUTER_API_KEY"):
        return RecipeGenerator(provider="openrouter")
    elif os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your-deepseek-api-key-here":
        return RecipeGenerator(provider="deepseek")
    else:
        pytest.skip("No API key configured (OPENROUTER_API_KEY or DEEPSEEK_API_KEY)")


@pytest.fixture(scope="module")
def structurer(load_env):
    """Create a structurer instance"""
    if os.getenv("OPENROUTER_API_KEY"):
        return RecipeStructurer()
    elif os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your-deepseek-api-key-here":
        return RecipeStructurer()
    else:
        pytest.skip("No API key configured")


# =============================================================================
# Unit Tests (No API calls)
# =============================================================================

class TestModels:
    """Test Pydantic models without API calls"""
    
    def test_metadata_creation(self):
        """Test Metadata model creation"""
        metadata = Metadata(
            title="Test Recipe",
            description="A test recipe",
            servings=4,
            difficulty="easy",
            recipeType="main_course"
        )
        assert metadata.title == "Test Recipe"
        assert metadata.servings == 4
        assert metadata.difficulty == "easy"
    
    def test_ingredient_creation(self):
        """Test Ingredient model creation"""
        ingredient = Ingredient(
            id="flour",
            name="all-purpose flour",
            quantity=200,
            unit="g",
            category="pantry"
        )
        assert ingredient.id == "flour"
        assert ingredient.quantity == 200
        assert ingredient.category == "pantry"
    
    def test_ingredient_optional_fields(self):
        """Test Ingredient with optional fields"""
        ingredient = Ingredient(
            id="salt",
            name="salt",
            quantity=None,
            unit=None,
            category="spice",
            optional=True,
            notes="to taste"
        )
        assert ingredient.optional is True
        assert ingredient.quantity is None
    
    def test_step_creation(self):
        """Test Step model creation"""
        step = Step(
            id="mix_dry",
            action="Mix flour and sugar",
            stepType="combine",
            uses=["flour", "sugar"],
            produces="dry_mix"
        )
        assert step.id == "mix_dry"
        assert "flour" in step.uses
        assert step.produces == "dry_mix"
    
    def test_step_with_requires(self):
        """Test Step with requires field for parallel dependencies"""
        step = Step(
            id="bake",
            action="Bake the cake",
            duration="PT30M",
            temperature=180,
            stepType="cook",
            isPassive=True,
            uses=["batter"],
            requires=["preheated_oven"],
            produces="baked_cake"
        )
        assert "preheated_oven" in step.requires
        assert step.isPassive is True
    
    def test_recipe_creation(self):
        """Test Recipe model creation"""
        recipe = Recipe(
            metadata=Metadata(
                title="Test",
                description="Test recipe",
                servings=4,
                difficulty="easy",
                recipeType="dessert"
            ),
            ingredients=[
                Ingredient(id="flour", name="flour", quantity=200, unit="g", category="pantry")
            ],
            tools=["bowl"],
            steps=[
                Step(id="step1", action="Mix", stepType="combine", uses=["flour"], produces="mixed")
            ],
            finalState="mixed"
        )
        assert recipe.metadata.title == "Test"
        assert len(recipe.ingredients) == 1
        assert len(recipe.steps) == 1
        assert recipe.finalState == "mixed"

    def test_graph_validation_rejects_empty_uses(self):
        """Test that graph validation rejects steps with empty uses (non-equipment)"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="empty `uses`"):
            Recipe(
                metadata=Metadata(
                    title="Test", description="Test", servings=4,
                    difficulty="easy", recipeType="dessert"
                ),
                ingredients=[
                    Ingredient(id="flour", name="flour", quantity=200, unit="g", category="pantry")
                ],
                steps=[
                    Step(id="step1", action="Cook something", stepType="cook", uses=[], produces="cooked")
                ],
                finalState="cooked"
            )

    def test_graph_validation_rejects_unknown_ref(self):
        """Test that graph validation rejects uses referencing unknown IDs"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="neither an ingredient ID nor a state"):
            Recipe(
                metadata=Metadata(
                    title="Test", description="Test", servings=4,
                    difficulty="easy", recipeType="dessert"
                ),
                ingredients=[
                    Ingredient(id="flour", name="flour", quantity=200, unit="g", category="pantry")
                ],
                steps=[
                    Step(id="step1", action="Mix", stepType="combine", uses=["flour", "ghost_ingredient"], produces="mixed")
                ],
                finalState="mixed"
            )

    def test_graph_validation_rejects_unused_ingredients(self):
        """Test that graph validation rejects unused ingredients"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="Unused ingredients"):
            Recipe(
                metadata=Metadata(
                    title="Test", description="Test", servings=4,
                    difficulty="easy", recipeType="dessert"
                ),
                ingredients=[
                    Ingredient(id="flour", name="flour", quantity=200, unit="g", category="pantry"),
                    Ingredient(id="sugar", name="sugar", quantity=100, unit="g", category="pantry"),
                ],
                steps=[
                    Step(id="step1", action="Mix flour", stepType="combine", uses=["flour"], produces="mixed")
                ],
                finalState="mixed"
            )

    def test_graph_validation_rejects_orphan_states(self):
        """Test that graph validation rejects states that are produced but never used"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="Orphan states"):
            Recipe(
                metadata=Metadata(
                    title="Test", description="Test", servings=4,
                    difficulty="easy", recipeType="dessert"
                ),
                ingredients=[
                    Ingredient(id="flour", name="flour", quantity=200, unit="g", category="pantry"),
                    Ingredient(id="sugar", name="sugar", quantity=100, unit="g", category="pantry"),
                ],
                steps=[
                    Step(id="step1", action="Mix flour", stepType="combine", uses=["flour"], produces="orphan_state"),
                    Step(id="step2", action="Mix sugar", stepType="combine", uses=["sugar"], produces="final")
                ],
                finalState="final"
            )

    def test_graph_validation_rejects_bad_final_state(self):
        """Test that graph validation rejects finalState not produced by any step"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="finalState"):
            Recipe(
                metadata=Metadata(
                    title="Test", description="Test", servings=4,
                    difficulty="easy", recipeType="dessert"
                ),
                ingredients=[
                    Ingredient(id="flour", name="flour", quantity=200, unit="g", category="pantry")
                ],
                steps=[
                    Step(id="step1", action="Mix", stepType="combine", uses=["flour"], produces="mixed")
                ],
                finalState="nonexistent_state"
            )

    def test_graph_validation_allows_preheat_empty_uses(self):
        """Test that graph validation allows preheat/equipment steps with empty uses"""
        recipe = Recipe(
            metadata=Metadata(
                title="Test", description="Test", servings=4,
                difficulty="easy", recipeType="dessert"
            ),
            ingredients=[
                Ingredient(id="flour", name="flour", quantity=200, unit="g", category="pantry")
            ],
            steps=[
                Step(id="preheat", action="Preheat the oven to 180°C", stepType="prep", uses=[], produces="preheated_oven"),
                Step(id="step1", action="Mix flour", stepType="combine", uses=["flour"], produces="batter"),
                Step(id="step2", action="Bake", stepType="cook", uses=["batter"], requires=["preheated_oven"], produces="cake")
            ],
            finalState="cake"
        )
        assert recipe.finalState == "cake"

    def test_graph_validation_multi_subrecipe(self):
        """Test a valid recipe with multiple sub-recipes and cross-references"""
        recipe = Recipe(
            metadata=Metadata(
                title="Poulet sauce", description="Poulet avec sauce", servings=4,
                difficulty="medium", recipeType="main_course"
            ),
            ingredients=[
                Ingredient(id="chicken", name="poulet", quantity=1, unit="kg", category="poultry"),
                Ingredient(id="cream", name="crème", quantity=200, unit="ml", category="dairy"),
                Ingredient(id="onion", name="oignon", quantity=1, unit="piece", category="produce"),
                Ingredient(id="salt", name="sel", quantity=None, unit=None, category="spice"),
            ],
            steps=[
                Step(id="season", action="Assaisonner le poulet", stepType="prep",
                        uses=["chicken", "salt"], produces="seasoned_chicken", subRecipe="poulet"),
                Step(id="cook_chicken", action="Cuire le poulet", stepType="cook",
                        uses=["seasoned_chicken"], produces="cooked_chicken", subRecipe="poulet"),
                Step(id="make_sauce", action="Préparer la sauce", stepType="cook",
                        uses=["onion", "cream"], produces="cream_sauce", subRecipe="sauce"),
                Step(id="assemble", action="Napper le poulet de sauce", stepType="serve",
                        uses=["cooked_chicken", "cream_sauce"], produces="poulet_sauce", subRecipe="assemblage"),
            ],
            finalState="poulet_sauce"
        )
        assert recipe.finalState == "poulet_sauce"
        assert len(recipe.steps) == 4


# =============================================================================
# Integration Tests (With API calls)
# =============================================================================

@pytest.mark.asyncio
class TestGenerator:
    """Integration tests for RecipeGenerator"""
    
    async def test_generate_simple_recipe(self, generator):
        """Test generating a simple recipe"""
        recipe = await generator.generate(SAMPLE_RECIPE_SIMPLE)
        
        assert isinstance(recipe, Recipe)
        assert recipe.metadata.title is not None
        assert len(recipe.ingredients) >= 5
        assert len(recipe.steps) >= 4
        assert recipe.finalState is not None
        print(f"✅ Generated: {recipe.metadata.title}")
    
    async def test_generate_french_recipe(self, generator):
        """Test generating a French recipe"""
        recipe = await generator.generate(SAMPLE_RECIPE_FRENCH)
        
        assert isinstance(recipe, Recipe)
        assert "veau" in recipe.metadata.title.lower() or "blanquette" in recipe.metadata.title.lower()
        assert recipe.metadata.nationality is not None
        print(f"✅ Generated French recipe: {recipe.metadata.title}")
    
    async def test_generate_filters_noise(self, generator):
        """Test that generator filters out webpage noise"""
        recipe = await generator.generate(SAMPLE_NOISY_WEBPAGE)
        
        assert isinstance(recipe, Recipe)
        assert "cookie" in recipe.metadata.title.lower()
        # Should not include comments or navigation in notes
        notes_text = " ".join(recipe.metadata.notes).lower() if recipe.metadata.notes else ""
        assert "user1" not in notes_text
        assert "footer" not in notes_text
        print(f"✅ Filtered noise, got: {recipe.metadata.title}")
    
    async def test_graph_structure_valid(self, generator):
        """Test that the graph structure is valid (uses/produces)"""
        recipe = await generator.generate(SAMPLE_RECIPE_SIMPLE)
        
        # Collect all ingredient IDs
        ingredient_ids = {ing.id for ing in recipe.ingredients}
        
        # Collect all produced states
        produced_states = set()
        for step in recipe.steps:
            produced_states.add(step.produces)
        
        # Verify each step's uses references valid sources
        for step in recipe.steps:
            for ref in step.uses:
                # Reference should be either an ingredient or a previously produced state
                is_valid = ref in ingredient_ids or ref in produced_states
                if not is_valid:
                    print(f"Warning: {step.id} uses '{ref}' which is not a known ingredient or state")
        
        # Final state should be produced by some step
        assert recipe.finalState in produced_states, \
            f"finalState '{recipe.finalState}' not found in produced states"
        
        print(f"✅ Graph structure valid: {len(recipe.steps)} steps")
    
    async def test_iso_duration_format(self, generator):
        """Test that durations use ISO 8601 format"""
        recipe = await generator.generate(SAMPLE_RECIPE_SIMPLE)
        
        for step in recipe.steps:
            if step.duration:
                assert step.duration.startswith("PT"), \
                    f"Duration '{step.duration}' should be ISO 8601 format (PTxM or PTxH)"
        
        if recipe.metadata.prepTime:
            assert recipe.metadata.prepTime.startswith("PT")
        if recipe.metadata.cookTime:
            assert recipe.metadata.cookTime.startswith("PT")
        
        print("✅ ISO 8601 duration format valid")


@pytest.mark.asyncio
class TestStructurer:
    """Integration tests for RecipeStructurer wrapper"""
    
    async def test_structure_from_text(self, structurer):
        """Test structuring from raw text"""
        recipe = await structurer.structure_from_text(SAMPLE_RECIPE_SIMPLE)
        
        assert isinstance(recipe, Recipe)
        assert recipe.metadata.title is not None
        print(f"✅ Structured: {recipe.metadata.title}")
    
    async def test_to_dict(self, structurer):
        """Test converting recipe to dictionary"""
        recipe = await structurer.structure_from_text(SAMPLE_RECIPE_SIMPLE)
        recipe_dict = structurer.to_dict(recipe)
        
        assert isinstance(recipe_dict, dict)
        assert "metadata" in recipe_dict
        assert "ingredients" in recipe_dict
        assert "steps" in recipe_dict
        assert "finalState" in recipe_dict
        print("✅ to_dict conversion works")


# =============================================================================
# CLI Runner
# =============================================================================

async def run_tests():
    """Run all tests manually"""
    load_dotenv()
    load_dotenv('../../.env')
    
    print("\n🧪 Running Tests...")
    print("=" * 60)
    
    # Unit tests
    print("\n📦 Unit Tests (no API)")
    print("-" * 40)
    
    test_models = TestModels()
    test_models.test_metadata_creation()
    print("✅ Metadata creation")
    
    test_models.test_ingredient_creation()
    print("✅ Ingredient creation")
    
    test_models.test_step_creation()
    print("✅ Step creation")
    
    test_models.test_recipe_creation()
    print("✅ Recipe creation")
    
    # Integration tests
    print("\n🌐 Integration Tests (with API)")
    print("-" * 40)
    
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY") and not (
        os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your-deepseek-api-key-here"
    ):
        print("⚠️  Skipping integration tests - no API key configured")
        return
    
    generator = RecipeGenerator(provider="openrouter" if os.getenv("OPENROUTER_API_KEY") else "deepseek")
    
    tests = TestGenerator()
    
    print("\n1️⃣ Testing simple recipe generation...")
    await tests.test_generate_simple_recipe(generator)
    
    print("\n2️⃣ Testing French recipe...")
    await tests.test_generate_french_recipe(generator)
    
    print("\n3️⃣ Testing noise filtering...")
    await tests.test_generate_filters_noise(generator)
    
    print("\n4️⃣ Testing graph structure...")
    await tests.test_graph_structure_valid(generator)
    
    print("\n5️⃣ Testing ISO duration format...")
    await tests.test_iso_duration_format(generator)
    
    print("\n" + "=" * 60)
    print("✨ All tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())
