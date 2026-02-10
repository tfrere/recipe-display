"""
Test du modèle NER spécialisé recettes : edwardjross/xlm-roberta-base-finetuned-recipe-all
Ce modèle décompose une ligne d'ingrédient en : NAME, QUANTITY, UNIT, STATE, SIZE, TEMP, DF
F1 = 0.967 sur le test set

Usage: python test_recipe_ner.py
"""

from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import json
from collections import defaultdict


def load_model():
    """Charge le modèle NER spécialisé recettes."""
    print("Chargement du modèle edwardjross/xlm-roberta-base-finetuned-recipe-all...")
    print("(premier lancement = téléchargement ~1GB, ensuite c'est en cache)\n")

    model_name = "edwardjross/xlm-roberta-base-finetuned-recipe-all"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)

    ner_pipeline = pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",  # Regroupe les sous-tokens
    )
    print("Modèle chargé !\n")
    return ner_pipeline


def parse_ingredient(ner_pipeline, ingredient_text: str) -> dict:
    """Parse un ingrédient et retourne les entités détectées."""
    results = ner_pipeline(ingredient_text)

    # Regrouper par type d'entité
    entities = defaultdict(list)
    for entity in results:
        tag = entity["entity_group"]
        word = entity["word"].strip()
        score = entity["score"]
        entities[tag].append({"text": word, "score": round(score, 4)})

    return {
        "input": ingredient_text,
        "entities": dict(entities),
        "raw": [
            {
                "tag": r["entity_group"],
                "text": r["word"].strip(),
                "score": round(r["score"], 4),
            }
            for r in results
        ],
    }


def display_result(result: dict):
    """Affiche le résultat de manière lisible."""
    print(f"  Input: \"{result['input']}\"")

    tag_colors = {
        "NAME": "🟢",
        "QUANTITY": "🔵",
        "UNIT": "🟡",
        "STATE": "🟠",
        "SIZE": "🟣",
        "TEMP": "🔴",
        "DF": "⚪",
    }

    for tag, items in result["entities"].items():
        icon = tag_colors.get(tag, "⚫")
        values = ", ".join(
            [f"{item['text']} ({item['score']:.1%})" for item in items]
        )
        print(f"    {icon} {tag:10s} → {values}")
    print()


def main():
    ner = load_model()

    # ═══════════════════════════════════════════════════════════
    # TEST 1 : Ingrédients classiques en anglais
    # ═══════════════════════════════════════════════════════════
    print("=" * 70)
    print("TEST 1 : Ingrédients classiques (anglais)")
    print("=" * 70)

    english_ingredients = [
        "2 cups all-purpose flour",
        "1/2 teaspoon fresh thyme, minced",
        "3 large eggs, beaten",
        "150 g unsalted butter, melted",
        "1 pound boneless skinless chicken breast, cut into cubes",
        "2 tablespoons extra virgin olive oil",
        "1 (14 oz) can diced tomatoes",
        "3 cloves garlic, finely minced",
        "1/4 cup freshly squeezed lemon juice",
        "salt and pepper to taste",
    ]

    for ing in english_ingredients:
        result = parse_ingredient(ner, ing)
        display_result(result)

    # ═══════════════════════════════════════════════════════════
    # TEST 2 : Ingrédients en français (le modèle est XLM = multilingue)
    # ═══════════════════════════════════════════════════════════
    print("=" * 70)
    print("TEST 2 : Ingrédients en français (test multilingue)")
    print("=" * 70)

    french_ingredients = [
        "200 g de farine",
        "3 cuillères à soupe d'huile d'olive",
        "150 g de beurre doux fondu",
        "1 kg de pommes de terre à chair ferme",
        "4 gousses d'ail émincées",
        "2 oignons moyens finement ciselés",
        "50 cl de crème fraîche épaisse",
        "1 bouquet de persil plat frais haché",
        "sel et poivre du moulin",
        "500 g de filet de saumon frais sans peau",
    ]

    for ing in french_ingredients:
        result = parse_ingredient(ner, ing)
        display_result(result)

    # ═══════════════════════════════════════════════════════════
    # TEST 3 : Cas difficiles / pièges
    # ═══════════════════════════════════════════════════════════
    print("=" * 70)
    print("TEST 3 : Cas difficiles et pièges")
    print("=" * 70)

    tricky_ingredients = [
        # Quantité vague
        "a pinch of saffron threads",
        # Deux ingrédients sur une ligne
        "salt and freshly ground black pepper",
        # Température
        "1 cup warm milk (about 110°F)",
        # Taille + état
        "2 large ripe avocados, peeled and diced",
        # Format bizarre
        "1-2 tablespoons honey, or to taste",
        # Ingrédient complexe
        "1 (400g) block extra-firm tofu, drained and pressed",
        # Frais/sec
        "2 teaspoons dried oregano",
        "1/4 cup fresh basil leaves, torn",
    ]

    for ing in tricky_ingredients:
        result = parse_ingredient(ner, ing)
        display_result(result)

    # ═══════════════════════════════════════════════════════════
    # TEST 4 : Simulation de cross-check avec un LLM
    # ═══════════════════════════════════════════════════════════
    print("=" * 70)
    print("TEST 4 : Simulation de cross-check NER vs LLM")
    print("=" * 70)

    # Simulons ce que Claude pourrait produire vs ce que le NER détecte
    simulated_checks = [
        {
            "source_text": "150g de beurre doux",
            "llm_output": {
                "name": "beurre doux",
                "quantity": 150,
                "unit": "g",
                "state": "fondu",  # ← HALLUCINATION : "fondu" n'est pas dans le texte
            },
        },
        {
            "source_text": "3 eggs",
            "llm_output": {
                "name": "eggs",
                "quantity": 3,
                "unit": None,
                "state": None,
            },
        },
        {
            "source_text": "2 tablespoons olive oil",
            "llm_output": {
                "name": "extra virgin olive oil",  # ← HALLUCINATION : "extra virgin" inventé
                "quantity": 2,
                "unit": "tablespoons",
                "state": None,
            },
        },
        {
            "source_text": "1 onion, finely chopped",
            "llm_output": {
                "name": "onion",
                "quantity": 1,
                "unit": None,
                "state": "finely chopped",  # ← CORRECT : c'est dans le texte
            },
        },
    ]

    for check in simulated_checks:
        ner_result = parse_ingredient(ner, check["source_text"])
        llm = check["llm_output"]
        ner_entities = ner_result["entities"]

        print(f"  Source: \"{check['source_text']}\"")
        print(f"  LLM dit:  name={llm['name']}, qty={llm['quantity']}, unit={llm['unit']}, state={llm['state']}")

        # Extraire ce que le NER a trouvé
        ner_name = " ".join([e["text"] for e in ner_entities.get("NAME", [])])
        ner_qty = " ".join([e["text"] for e in ner_entities.get("QUANTITY", [])])
        ner_unit = " ".join([e["text"] for e in ner_entities.get("UNIT", [])])
        ner_state = " ".join([e["text"] for e in ner_entities.get("STATE", [])])

        print(f"  NER dit:  name={ner_name or '∅'}, qty={ner_qty or '∅'}, unit={ner_unit or '∅'}, state={ner_state or '∅'}")

        # Détecter les divergences
        issues = []
        if llm.get("state") and not ner_state:
            issues.append(f"⚠️  HALLUCINATION probable : LLM dit state=\"{llm['state']}\" mais NER ne détecte rien")
        if llm.get("name") and ner_name and llm["name"].lower() != ner_name.lower():
            # Vérifier si le LLM a ajouté des mots
            llm_words = set(llm["name"].lower().split())
            ner_words = set(ner_name.lower().split())
            added = llm_words - ner_words
            if added:
                issues.append(f"⚠️  HALLUCINATION probable : LLM ajoute \"{' '.join(added)}\" au nom")

        if issues:
            for issue in issues:
                print(f"  {issue}")
        else:
            print("  ✅ Cohérent — pas de divergence détectée")
        print()

    # ═══════════════════════════════════════════════════════════
    # Résumé
    # ═══════════════════════════════════════════════════════════
    print("=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print("""
Le modèle NER spécialisé recettes :
- Parse les ingrédients en composants (nom, quantité, unité, état, taille, température)
- F1 = 0.967 → se trompe dans ~3% des cas
- Déterministe : même input = même output, toujours
- Pas d'hallucination possible (il classifie, il n'invente pas)
- Multilingue (XLM-RoBERTa) → test en français possible

Utilisé en cross-check avec un LLM :
- Si le LLM dit "fondu" mais le NER ne voit pas "fondu" dans le texte → flag
- Si le LLM dit "extra virgin" mais le NER ne voit que "olive oil" → flag
- Complémentaire : le NER attrape ce que le LLM invente
    """)


if __name__ == "__main__":
    main()
