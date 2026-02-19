# Rapport d'Audit Adversarial LLM — Pipeline RecipeV2

**Date :** 10 Février 2026  
**Méthode :** Claude Sonnet 4 (via OpenRouter) compare le JSON structuré RecipeV2 avec le texte source original scrapé  
**Corpus :** 7 recettes (3 EN, 4 FR)

---

## 1. Vue d'ensemble

| Recette | Score | Issues | Scrape OK ? |
|---------|-------|--------|-------------|
| 1-Pot Golden Curry Lentil Soup | 8/10 | 5 | ✅ |
| Caviar d'Aubergine | 8/10 | 9 | ✅ |
| One Pot Creamy Cajun Chicken Pasta | 6/10 | 4 | ✅ |
| Risotto Printanier aux Asperges | 1/10 | 2 | ❌ Scrape vide |
| Rouleaux de Printemps Vegan | 1/10 | 1 | ❌ Scrape vide |
| Tarte épinards fêta | ~6/10 | ≥5 | ✅ (parse fail) |
| Tartines Figues Chèvre Miel | 8/10 | 2 | ✅ |

**Score moyen (recettes avec scrape fonctionnel) : 7.2/10**  
**Issues totales (hors scrape vides) : ~25**

---

## 2. Bugs confirmés par vérification manuelle

### 2.1 Temps incorrects (⚠️ BUG CRITIQUE — systémique)

Comparaison JSON-LD source vs notre JSON stocké :

| Recette | Champ | Source (JSON-LD) | Notre JSON | Écart |
|---------|-------|-----------------|-----------|-------|
| Curry Lentil | `prepTime` | **PT5M** | PT10M | +5min |
| Curry Lentil | `totalTime` | PT30M | **24.0** (float!) | format + valeur |
| Cajun Chicken | `prepTime` | **PT10M** | PT15M | +5min |
| Cajun Chicken | `totalTime` | PT30M | **34.0** (float!) | format + valeur |
| Caviar Aubergine | `cookTime` | **PT45M** | PT35M | -10min |
| Caviar Aubergine | `totalTime` | PT55M | **35.0** (float!) | format + valeur |
| Risotto | `cookTime` | **PT20M** | PT35M | +15min |
| Risotto | `totalTime` | PT40M | **66.0** (float!) | format + valeur |
| Rouleaux | `totalTime` | PT30M | **9.0** (float!) | format + valeur |
| Tartines | `totalTime` | PT20M | **12.0** (float!) | format + valeur |
| Tarte | `prepTime` | **PT40M** | PT30M | -10min |
| Tarte | `cookTime` | **PT25M** | PT70M | +45min! |
| Tarte | `totalTime` | PT65M | **70.0** (float!) | format + valeur |

**Constat :** `totalTime` n'est **jamais** au bon format — c'est un `float` au lieu d'un ISO 8601 string. Le champ n'est pas défini dans le schéma Pydantic (`MetadataV2` n'a pas de `totalTime`), donc il n'est pas validé. De plus, les `prepTime` et `cookTime` sont souvent approximés par le LLM au lieu d'utiliser les vraies valeurs JSON-LD.

### 2.2 Unités EN vs FR — FAUX POSITIF du reviewer

Le reviewer a flaggé que les unités du Caviar d'Aubergine devraient être `c-à-s`, `gousse`, `branches` au lieu de `tbsp`, `clove`, `sprig`.

**Verdict : FAUX POSITIF.** Notre pipeline normalise intentionnellement toutes les unités en anglais canonique. C'est un choix de design (standardisation, nutrition lookup). Le reviewer ne connaît pas cette règle.

### 2.3 Ingrédients simplifiés (confirmé, mineur)

| Recette | Ingrédient | Source | Notre JSON |
|---------|-----------|--------|-----------|
| Curry | `coconut_milk` | "canned light coconut milk" | "coconut milk" |
| Curry | `red_lentils` | "red or golden lentils" | "red lentils" |
| Tartines | `fresh_thyme` | "thym frais ou thym sec" | "thym frais" (pas d'alternative) |
| Curry | `serrano_pepper` | "1 small serrano pepper" | unit=null ("small" perdu) |

**Verdict :** Simplifications mineures. Le nom de l'ingrédient est un peu tronqué mais reste correct. L'info manquante devrait aller dans `notes` ou `preparation`.

### 2.4 Notes manquantes (confirmé, mineur)

Le reviewer signale des notes de substitution manquantes (ex: "or sub other seasonal vegetable" pour les carottes du Curry). Vérification : **13 des 96 ingrédients totaux ont des notes** (14%). C'est effectivement faible — beaucoup de tips culinaires de la source sont perdus.

### 2.5 Scraping cassé sur Free The Pickle (CRITIQUE)

2 recettes sur 7 (Risotto, Rouleaux) ont un scrape qui retourne quasi-rien (32 et 44 chars). Le reviewer a raison de donner 1/10 — mais c'est un bug du **scraper**, pas du structureur.

### 2.6 Parse fail du reviewer (Tarte épinards)

Le reviewer LLM a retourné un JSON avec des types incorrects (`list` au lieu de `str` dans `step_corrections`). C'est un problème de notre prompt — le LLM ne respecte pas toujours strictement le schéma Pydantic de `ReviewResult`.

---

## 3. Catégorisation des problèmes

### Problèmes SYSTÉMIQUES (affectent toutes les recettes)

1. **`totalTime` est un float, pas ISO 8601** — Le schéma Pydantic n'a pas ce champ, donc pas de validation. Le LLM invente un nombre au lieu de calculer `prepTime + cookTime`.
2. **`prepTime`/`cookTime` approximés** — Le LLM devrait extraire les valeurs JSON-LD de la source au lieu de deviner.
3. **Peu de notes/substitutions** — Les tips culinaires sont systématiquement perdus.

### Problèmes du SCRAPER (pas du structureur)

4. **Free The Pickle scrape vide** — 2/4 recettes FTP n'ont pas de contenu scrapé correctement (probablement du contenu rendu côté client JS).

### Problèmes du REVIEWER lui-même

5. **Faux positifs sur les unités FR** — Le reviewer ne sait pas que les unités EN sont normalisées by design.
6. **Parse fail (types incorrects)** — 1/7 recettes a un parse failure.
7. **Source coupée** — Le reviewer scrape la source indépendamment, parfois avec un résultat différent du pipeline original.

---

## 4. Recommandations

### Quick wins (safe auto-fix)
- [ ] Ajouter `totalTime: Optional[str]` au schéma `MetadataV2` en ISO 8601, calculé comme `prepTime + cookTime`
- [ ] Extraire `prepTime`, `cookTime`, `totalTime` du JSON-LD de la source (structured data) plutôt que de laisser le LLM deviner
- [ ] Améliorer le prompt du reviewer avec la règle "les unités sont toujours en anglais canonique"

### Améliorations pipeline
- [ ] Enrichir le prompt Pass 2 pour capturer les notes de substitution dans `IngredientV2.notes`
- [ ] Diagnostiquer le scraping FTP (JS-rendered content ?)

### Intégration reviewer
- [ ] Ajouter Pass 3 reviewer au pipeline, avec schema strict + retry si parse fail
- [ ] Implémenter auto-fix safe (metadata, notes) avec validation Pydantic

---

## 5. Données brutes

Les résultats JSON complets sont dans `experiments/review_results.json`.
