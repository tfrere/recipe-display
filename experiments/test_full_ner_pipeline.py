"""
Test complet du pipeline NER sur de vraies recettes.

Simule le flow :
  Pass 1 output (texte avec traductions EN) → NER parsing → IngredientV2

Teste sur 3 recettes complètes :
  1. Blanquette de veau (FR classique)
  2. Houmous à la betterave (FR végane)
  3. Pad Thai (EN complexe)

Usage: python3 test_full_ner_pipeline.py
"""

import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    pipeline,
)


# ═══════════════════════════════════════════════════════════════════
# MODÈLE NER
# ═══════════════════════════════════════════════════════════════════


def load_ner_model():
    """Charge le modèle NER spécialisé recettes."""
    print("⏳ Chargement du modèle NER...")
    model_name = "edwardjross/xlm-roberta-base-finetuned-recipe-all"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    ner = pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
    )
    print("✅ Modèle chargé\n")
    return ner


# ═══════════════════════════════════════════════════════════════════
# PARSING D'UNE LIGNE D'INGRÉDIENT
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ParsedIngredient:
    """Résultat du parsing NER d'un ingrédient."""

    id: str
    name: str  # nom original (langue de la recette)
    name_en: str  # nom anglais
    quantity: Optional[float] = None
    unit: Optional[str] = None
    category: str = "other"
    preparation: Optional[str] = None
    notes: Optional[str] = None
    optional: bool = False
    confidence: float = 0.0
    ner_raw: dict = field(default_factory=dict)


def make_id(name_en: str) -> str:
    """Convertit un nom anglais en snake_case ID."""
    # Retirer les caractères spéciaux
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", name_en.lower().strip())
    # Remplacer les espaces par des underscores
    return re.sub(r"\s+", "_", clean)


def parse_quantity(qty_str: str) -> Optional[float]:
    """Convertit une chaîne quantité en float."""
    if not qty_str:
        return None

    qty_str = qty_str.strip()

    # Fractions Unicode
    fraction_map = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 0.333, "⅔": 0.667}
    for frac, val in fraction_map.items():
        if frac in qty_str:
            # "1½" → 1.5
            rest = qty_str.replace(frac, "").strip()
            return float(rest) + val if rest else val

    # Fractions textuelles : "1/2", "3/4"
    if "/" in qty_str:
        parts = qty_str.split()
        total = 0.0
        for part in parts:
            if "/" in part:
                num, den = part.split("/")
                total += float(num) / float(den)
            else:
                total += float(part)
        return total

    # Range : "1-2" → prendre le premier
    if "-" in qty_str:
        return float(qty_str.split("-")[0])

    try:
        return float(qty_str)
    except ValueError:
        return None


def ner_parse_ingredient(ner_pipeline, english_text: str) -> dict:
    """Parse une ligne d'ingrédient anglaise avec le NER."""
    results = ner_pipeline(english_text)

    entities = defaultdict(list)
    for entity in results:
        tag = entity["entity_group"]
        word = entity["word"].strip()
        score = entity["score"]
        entities[tag].append({"text": word, "score": score})

    return dict(entities)


def parse_pass1_ingredient_line(
    ner_pipeline,
    line: str,
) -> Optional[ParsedIngredient]:
    """
    Parse une ligne d'ingrédient au format Pass 1 :
    "250g champignons de Paris [mushrooms] {produce}, émincés [sliced]"
    "sel [salt] {spice} (à volonté)"
    "3 cuillères à soupe d'huile d'olive [olive oil] {pantry}"

    Retourne un ParsedIngredient ou None si la ligne est vide.
    """
    line = line.strip()
    if not line:
        return None

    # Extraire la catégorie {category}
    category_match = re.search(r"\{(\w+)\}", line)
    category = category_match.group(1) if category_match else "other"

    # Extraire les traductions anglaises [english_name]
    en_matches = re.findall(r"\[([^\]]+)\]", line)
    name_en = en_matches[0] if en_matches else ""
    preparation_en = en_matches[1] if len(en_matches) > 1 else None

    # Vérifier si optionnel
    optional = "(optionnel)" in line.lower() or "(optional)" in line.lower() or "(à volonté)" in line.lower()

    # Extraire les notes entre ()
    notes_match = re.search(r"\(([^)]+)\)", line)
    notes = notes_match.group(1) if notes_match and not optional else None

    # Nettoyer la ligne pour extraire le nom original
    # Retirer les annotations
    clean_line = re.sub(r"\{[^}]+\}", "", line)
    clean_line = re.sub(r"\[[^\]]+\]", "", clean_line)
    clean_line = re.sub(r"\([^)]+\)", "", clean_line)
    clean_line = clean_line.strip().rstrip(",").strip()

    # Le nom original c'est la ligne nettoyée (sans qty/unit — on laisse ça au NER)
    name_original = clean_line

    # ─── NER sur la version anglaise ───
    # Construire la chaîne anglaise à parser
    en_text_for_ner = ""
    if name_en:
        # Reconstruire la ligne en anglais pour le NER
        # On prend le texte brut, on remplace le nom par la version EN
        # Mais on garde les quantités/unités originales car le NER les comprend

        # Extraire qty+unit du début de la ligne originale
        qty_unit_match = re.match(
            r"^([\d½¼¾⅓⅔/.,\-\s]+)\s*(g|kg|ml|cl|l|lb|oz|tsp|tbsp|cup|cups|"
            r"cuillères?\s+à\s+(?:soupe|café)|"
            r"pieces?|piece|"
            r"branches?|brins?|gousses?|feuilles?|tranches?|"
            r"tablespoons?|teaspoons?|pounds?|ounces?|"
            r"pinch|bunch)\s*",
            clean_line,
            re.IGNORECASE,
        )

        if qty_unit_match:
            qty_str = qty_unit_match.group(1).strip()
            unit_str = qty_unit_match.group(2).strip()
            # Traduire les unités FR → EN
            unit_map = {
                "cuillères à soupe": "tablespoons",
                "cuillère à soupe": "tablespoon",
                "cuillères à café": "teaspoons",
                "cuillère à café": "teaspoon",
                "gousses": "cloves",
                "gousse": "clove",
                "branches": "sprigs",
                "branche": "sprig",
                "brins": "sprigs",
                "brin": "sprig",
                "feuilles": "leaves",
                "feuille": "leaf",
                "tranches": "slices",
                "tranche": "slice",
            }
            unit_en = unit_map.get(unit_str.lower(), unit_str)
            en_text_for_ner = f"{qty_str} {unit_en} {name_en}"
        else:
            en_text_for_ner = name_en

        if preparation_en:
            en_text_for_ner += f", {preparation_en}"

    if not en_text_for_ner:
        en_text_for_ner = clean_line  # Fallback

    # Parser avec le NER
    ner_entities = ner_parse_ingredient(ner_pipeline, en_text_for_ner)

    # Extraire les valeurs NER
    ner_qty_raw = " ".join([e["text"] for e in ner_entities.get("QUANTITY", [])])
    ner_unit = " ".join([e["text"] for e in ner_entities.get("UNIT", [])])
    ner_name = " ".join([e["text"] for e in ner_entities.get("NAME", [])])
    ner_state = " ".join([e["text"] for e in ner_entities.get("STATE", [])])

    # Confiance moyenne
    all_scores = [e["score"] for ents in ner_entities.values() for e in ents]
    avg_confidence = sum(all_scores) / len(all_scores) if all_scores else 0.0

    # Construire l'ingrédient parsé
    quantity = parse_quantity(ner_qty_raw)
    unit = ner_unit if ner_unit else None
    preparation = preparation_en or (ner_state if ner_state else None)
    final_name_en = name_en if name_en else ner_name

    ingredient_id = make_id(final_name_en) if final_name_en else make_id(name_original)

    return ParsedIngredient(
        id=ingredient_id,
        name=name_original,
        name_en=final_name_en,
        quantity=quantity,
        unit=unit,
        category=category,
        preparation=preparation,
        notes=notes,
        optional=optional,
        confidence=avg_confidence,
        ner_raw={
            "input": en_text_for_ner,
            "entities": ner_entities,
        },
    )


# ═══════════════════════════════════════════════════════════════════
# DONNÉES DE TEST : SORTIES SIMULÉES DE PASS 1
# ═══════════════════════════════════════════════════════════════════


BLANQUETTE_PASS1_INGREDIENTS = """
1 kg veau épaule [veal shoulder] {meat}, coupé en morceaux [cut into chunks]
3 l eau [water] {beverage}
2 branches thym frais [fresh thyme] {produce}
4 carottes [carrots] {produce}, épluchées et coupées [peeled and cut into chunks]
2 oignons [onions] {produce}, épluchés et coupés en quatre [peeled and quartered]
60 g beurre [butter] {dairy}
60 g farine [flour] {pantry}
20 cl crème liquide [heavy cream] {dairy}
sel [salt] {spice} (à volonté)
poivre [pepper] {spice} (à volonté)
""".strip()


HOUMOUS_PASS1_INGREDIENTS = """
200 g betterave crue [raw beets] {produce}
400 g pois chiches [chickpeas] {pantry}, égouttés et rincés [drained and rinsed]
60 g tahini [tahini] {pantry}
3 cuillères à soupe huile d'olive [olive oil] {pantry}
3 cuillères à soupe jus de citron [lemon juice] {produce}
1 gousse ail [garlic] {produce}
0.5 cuillère à café cumin [cumin] {spice}
0.5 cuillère à café sel [salt] {spice}
50 ml eau [water] {pantry}
persil haché [chopped parsley] {produce} (optionnel)
za'atar [za'atar] {spice} (optionnel)
radis [radishes] {produce}, émincés [sliced] (optionnel)
pignons de pin [pine nuts] {pantry} (optionnel)
""".strip()


PAD_THAI_PASS1_INGREDIENTS = """
200 g rice noodles [rice noodles] {pantry}
2 tablespoons vegetable oil [vegetable oil] {pantry}
3 cloves garlic [garlic] {produce}, minced [minced]
200 g firm tofu [firm tofu] {pantry}, cubed [cubed]
2 eggs [eggs] {egg}
1 cup bean sprouts [bean sprouts] {produce}
3 tablespoons fish sauce [fish sauce] {condiment}
2 tablespoons tamarind paste [tamarind paste] {condiment}
1 tablespoon palm sugar [palm sugar] {pantry}
1/4 cup roasted peanuts [roasted peanuts] {pantry}, crushed [crushed]
2 green onions [green onions] {produce}, sliced [sliced]
1 lime [lime] {produce}, cut into wedges [cut into wedges]
1 pinch dried chili flakes [dried chili flakes] {spice} (optional)
""".strip()


# ═══════════════════════════════════════════════════════════════════
# COMPARAISON AVEC LES RECETTES EXISTANTES
# ═══════════════════════════════════════════════════════════════════


def compare_with_existing(parsed: list[ParsedIngredient], existing_json_path: str):
    """Compare les ingrédients NER parsés avec ceux d'une recette JSON existante."""
    try:
        with open(existing_json_path) as f:
            recipe = json.load(f)
    except FileNotFoundError:
        print(f"  ⚠️  Fichier {existing_json_path} non trouvé, skip comparaison\n")
        return

    existing = recipe.get("ingredients", [])

    print(f"\n  {'─' * 60}")
    print(f"  COMPARAISON AVEC LA RECETTE EXISTANTE ({len(existing)} ingrédients)")
    print(f"  {'─' * 60}")

    # Matcher par name_en ou name
    matched = 0
    mismatches = []

    for ex in existing:
        ex_name_en = ex.get("name_en", ex.get("name", "")).lower()
        ex_name = ex.get("name", "").lower()
        ex_qty = ex.get("quantity")
        ex_unit = ex.get("unit")

        # Chercher le match dans les parsés
        best_match = None
        for p in parsed:
            if (
                p.name_en.lower() == ex_name_en
                or p.name_en.lower() in ex_name
                or ex_name_en in p.name_en.lower()
            ):
                best_match = p
                break

        if best_match:
            matched += 1
            issues = []

            # Comparer quantité
            if ex_qty is not None and best_match.quantity is not None:
                if abs(ex_qty - best_match.quantity) > 0.1:
                    issues.append(
                        f"qty: existant={ex_qty} vs NER={best_match.quantity}"
                    )

            # Comparer unité
            if ex_unit and best_match.unit:
                if ex_unit.lower() != best_match.unit.lower():
                    issues.append(
                        f"unit: existant={ex_unit} vs NER={best_match.unit}"
                    )

            # Comparer catégorie
            if ex.get("category") and best_match.category:
                if ex["category"] != best_match.category:
                    issues.append(
                        f"cat: existant={ex['category']} vs NER={best_match.category}"
                    )

            if issues:
                mismatches.append((ex_name_en or ex_name, issues))
                print(f"    ⚠️  {ex_name_en or ex_name}: {', '.join(issues)}")
            else:
                print(f"    ✅ {ex_name_en or ex_name}: parfait match")
        else:
            print(f"    ❌ {ex_name_en or ex_name}: pas trouvé dans le NER")

    print(f"\n    Résultat: {matched}/{len(existing)} matchés, {len(mismatches)} divergences")


# ═══════════════════════════════════════════════════════════════════
# FUZZY MATCHING (simulation de la correction d'IDs)
# ═══════════════════════════════════════════════════════════════════


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calcule la distance de Levenshtein entre deux chaînes."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def fuzzy_match_id(ref: str, valid_ids: set[str], max_distance: int = 3) -> Optional[str]:
    """Trouve l'ID le plus proche par distance de Levenshtein."""
    if ref in valid_ids:
        return ref

    best_match = None
    best_dist = max_distance + 1

    for valid_id in valid_ids:
        dist = levenshtein_distance(ref, valid_id)
        if dist < best_dist:
            best_dist = dist
            best_match = valid_id

    return best_match if best_dist <= max_distance else None


def test_fuzzy_matching(parsed: list[ParsedIngredient]):
    """Simule ce qui se passe quand le LLM se trompe dans les IDs."""
    valid_ids = {p.id for p in parsed}

    # Simuler des erreurs typiques du LLM
    llm_refs = {
        # Erreurs courantes
        "veal_shoulder": "veal_shoulder",  # exact match
        "butter": "butter",  # exact match
        "heavy_creme": "heavy_cream",  # typo
        "onion": "onions",  # singulier vs pluriel
        "carrot": "carrots",  # singulier vs pluriel
        "olive_oils": "olive_oil",  # pluriel ajouté
        "lemon_juic": "lemon_juice",  # typo
        "garlic_clove": "garlic",  # nom plus long
        "totally_wrong_ingredient": None,  # aucun match
    }

    print(f"\n  {'─' * 60}")
    print("  TEST FUZZY MATCHING (simulation erreurs LLM)")
    print(f"  {'─' * 60}")
    print(f"  IDs valides: {sorted(valid_ids)}\n")

    for wrong_ref, expected in llm_refs.items():
        match = fuzzy_match_id(wrong_ref, valid_ids)
        status = "✅" if match else "❌"
        if match and expected and match != expected:
            status = "⚠️"

        if match:
            dist = levenshtein_distance(wrong_ref, match)
            print(f"    {status} '{wrong_ref}' → '{match}' (distance={dist})")
        else:
            print(f"    {status} '{wrong_ref}' → AUCUN MATCH")


# ═══════════════════════════════════════════════════════════════════
# EXÉCUTION DES TESTS
# ═══════════════════════════════════════════════════════════════════


def run_recipe_test(
    ner_pipeline,
    recipe_name: str,
    ingredient_lines: str,
    existing_json: Optional[str] = None,
):
    """Exécute le test complet pour une recette."""
    print("=" * 70)
    print(f"RECETTE : {recipe_name}")
    print("=" * 70)

    lines = [l for l in ingredient_lines.split("\n") if l.strip()]
    parsed_ingredients: list[ParsedIngredient] = []

    start = time.time()

    for line in lines:
        result = parse_pass1_ingredient_line(ner_pipeline, line)
        if result:
            parsed_ingredients.append(result)

    elapsed = time.time() - start

    # Affichage des résultats
    print(f"\n  ⏱️  Temps de parsing : {elapsed:.3f}s pour {len(parsed_ingredients)} ingrédients")
    print(f"  📊 Moyenne : {elapsed / len(parsed_ingredients) * 1000:.1f}ms / ingrédient\n")

    for ing in parsed_ingredients:
        opt_tag = " (optionnel)" if ing.optional else ""
        conf_bar = "█" * int(ing.confidence * 10) + "░" * (10 - int(ing.confidence * 10))
        print(f"  {'─' * 60}")
        print(f"  ID:           {ing.id}")
        print(f"  Nom original: {ing.name}")
        print(f"  Nom EN:       {ing.name_en}")
        print(f"  Quantité:     {ing.quantity} {ing.unit or ''}{opt_tag}")
        print(f"  Catégorie:    {ing.category}")
        print(f"  Préparation:  {ing.preparation or '—'}")
        print(f"  Notes:        {ing.notes or '—'}")
        print(f"  Confiance:    {conf_bar} {ing.confidence:.1%}")
        print(f"  NER input:    \"{ing.ner_raw.get('input', '')}\"")

        # Détail des entités NER
        ner_ents = ing.ner_raw.get("entities", {})
        if ner_ents:
            parts = []
            for tag, items in ner_ents.items():
                vals = ", ".join(f"{i['text']}({i['score']:.0%})" for i in items)
                parts.append(f"{tag}={vals}")
            print(f"  NER détail:   {' | '.join(parts)}")

    # Comparaison avec existant
    if existing_json:
        compare_with_existing(parsed_ingredients, existing_json)

    # Test fuzzy matching
    test_fuzzy_matching(parsed_ingredients)

    # Générer le JSON IngredientV2
    print(f"\n  {'─' * 60}")
    print("  SORTIE JSON (format IngredientV2)")
    print(f"  {'─' * 60}")

    ingredients_json = []
    for ing in parsed_ingredients:
        obj = {
            "id": ing.id,
            "name": ing.name,
            "name_en": ing.name_en,
            "quantity": ing.quantity,
            "unit": ing.unit,
            "category": ing.category,
            "preparation": ing.preparation,
            "notes": ing.notes,
            "optional": ing.optional,
        }
        ingredients_json.append(obj)

    print(json.dumps(ingredients_json, indent=2, ensure_ascii=False))
    print()

    return parsed_ingredients


def main():
    ner = load_ner_model()

    # ─── Test 1 : Blanquette de veau ───
    blanquette_results = run_recipe_test(
        ner,
        "Blanquette de Veau (FR → EN)",
        BLANQUETTE_PASS1_INGREDIENTS,
        existing_json="example_recipe_v2.json",
    )

    # ─── Test 2 : Houmous à la betterave ───
    houmous_results = run_recipe_test(
        ner,
        "Houmous à la betterave (FR → EN)",
        HOUMOUS_PASS1_INGREDIENTS,
        existing_json="server/packages/recipe_scraper/data/recipes/houmous-a-la-betterave.recipe.json",
    )

    # ─── Test 3 : Pad Thai (anglais natif) ───
    padthai_results = run_recipe_test(
        ner,
        "Pad Thai (EN natif)",
        PAD_THAI_PASS1_INGREDIENTS,
    )

    # ═══════════════════════════════════════════════════════════════
    # RÉSUMÉ GLOBAL
    # ═══════════════════════════════════════════════════════════════
    print("=" * 70)
    print("RÉSUMÉ GLOBAL")
    print("=" * 70)

    all_results = blanquette_results + houmous_results + padthai_results
    total = len(all_results)
    high_conf = sum(1 for r in all_results if r.confidence >= 0.90)
    med_conf = sum(1 for r in all_results if 0.70 <= r.confidence < 0.90)
    low_conf = sum(1 for r in all_results if r.confidence < 0.70)

    has_qty = sum(1 for r in all_results if r.quantity is not None)
    has_unit = sum(1 for r in all_results if r.unit is not None)
    has_prep = sum(1 for r in all_results if r.preparation is not None)
    has_name_en = sum(1 for r in all_results if r.name_en)

    avg_conf = sum(r.confidence for r in all_results) / total if total else 0

    print(f"""
  Ingrédients totaux parsés: {total}

  Confiance:
    Haute  (≥90%):  {high_conf}/{total} ({high_conf / total:.0%})
    Moyenne (70-90%): {med_conf}/{total} ({med_conf / total:.0%})
    Basse  (<70%):  {low_conf}/{total} ({low_conf / total:.0%})
    Moyenne globale: {avg_conf:.1%}

  Couverture:
    Avec quantité:    {has_qty}/{total} ({has_qty / total:.0%})
    Avec unité:       {has_unit}/{total} ({has_unit / total:.0%})
    Avec préparation: {has_prep}/{total} ({has_prep / total:.0%})
    Avec nom EN:      {has_name_en}/{total} ({has_name_en / total:.0%})

  IDs uniques générés: {len(set(r.id for r in all_results))} / {total}
  IDs dupliqués: {total - len(set(r.id for r in all_results))}
    """)

    # Lister les ingrédients à faible confiance
    if low_conf > 0:
        print("  ⚠️  Ingrédients à faible confiance (<70%):")
        for r in all_results:
            if r.confidence < 0.70:
                print(f"    - {r.name} [{r.name_en}] → {r.confidence:.1%}")
                print(f"      NER input: \"{r.ner_raw.get('input', '')}\"")
        print()

    # Vérifier les doublons d'ID
    id_counts = defaultdict(int)
    for r in all_results:
        id_counts[r.id] += 1
    dupes = {k: v for k, v in id_counts.items() if v > 1}
    if dupes:
        print("  ⚠️  IDs dupliqués (nécessitent un suffixe):")
        for id_, count in dupes.items():
            print(f"    - '{id_}' apparaît {count} fois")
        print()


if __name__ == "__main__":
    main()
