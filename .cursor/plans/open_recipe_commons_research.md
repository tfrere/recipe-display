# OpenRecipes Commons — Rapport de recherche complet

> Recherche effectuée le 10 février 2026

---

## Table des matières

1. [L'état du marché des recettes ouvertes](#1-létat-du-marché-des-recettes-ouvertes)
2. [Les gestionnaires de recettes open source](#2-les-gestionnaires-de-recettes-open-source)
3. [Les formats d'échange de recettes](#3-les-formats-déchange-de-recettes)
4. [Les APIs commerciales](#4-les-apis-commerciales)
5. [La recherche académique](#5-la-recherche-académique)
6. [Les communs alimentaires (modèles d'inspiration)](#6-les-communs-alimentaires-modèles-dinspiration)
7. [Les ressources Hugging Face exploitables](#7-les-ressources-hugging-face-exploitables)
8. [Stratégie de vérification LLM en 2026](#8-stratégie-de-vérification-llm-en-2026)
9. [Synthèse : le trou dans le marché](#9-synthèse--le-trou-dans-le-marché)
10. [Recommandation : le modèle "commun décentralisé"](#10-recommandation--le-modèle-commun-décentralisé)

---

## 1. L'état du marché des recettes ouvertes

### OpenRecipes (openrecip.es) — MORT

- Créé après la fermeture de Punchfork (qui a emporté les données des utilisateurs)
- Seulement des "bookmarks" de recettes (métadonnées, pas les instructions)
- Format schema.org Recipe, dumps JSON
- **Archivé sur GitHub depuis 2018, plus aucune activité**
- Leçon : le projet n'avait pas d'UX de consommation, juste de la data brute → personne n'a contribué

### OpenRecipeDB (openrecipedb.org)

- Serveur open source (GPL-3.0)
- Très peu d'activité, projet marginal
- Pas de communauté visible

### TheMealDB (themealdb.com)

- API gratuite, ~599 recettes, ~877 ingrédients
- Données très basiques : texte plat, pas de structuration avancée
- Populaire chez les développeurs pour des projets d'apprentissage
- Pas vraiment un commun : propriétaire, API key requise

### Wikibooks Cookbook

- Quelques milliers de recettes en texte libre sur Wikibooks
- Aucune structuration (c'est du wiki classique)
- Pas d'API, pas de modèle de données exploitable
- Communauté très faible, qualité inégale
- **Le "Wikipedia des recettes" a été tenté ici, et ça n'a pas pris** — parce que le format texte brut n'apporte aucune valeur ajoutée vs un blog

---

## 2. Les gestionnaires de recettes open source

### Tandoor Recipes — 7 900+ stars GitHub

- Django + Vue.js, MIT license
- Import depuis des sites web (ld+json, microdata)
- Meal planning, shopping lists, scaling, cookbooks
- **open-tandoor-data** : repo de données structurées (aliments, unités, supermarchés) — 66 stars, 531 commits
- Usage : **personnel ou petit groupe**, pas un commun public

### Mealie

- Python + Nuxt.js, très populaire en self-hosting
- Import web, meal planning, shopping lists
- Multi-utilisateurs
- Même logique : **outil personnel**, pas de plateforme communautaire

### Grocy, Recipya, ManageMeals

- Alternatives similaires, orientées gestion domestique
- Aucun ne vise un commun ouvert

### Paprika (commercial)

- ~40$ multi-appareils
- Très poli mais propriétaire et fermé

**Verdict** : ces outils sont des "Notion pour recettes" — excellents pour l'usage perso, mais aucun ne construit de ressource commune. La donnée reste cloisonnée chez chaque utilisateur.

---

## 3. Les formats d'échange de recettes

### Schema.org Recipe

- Le standard web pour le SEO (JSON-LD)
- Utilisé par tous les blogs de cuisine pour Google
- **Très plat** : texte pour les ingrédients, texte pour les étapes
- Pas de notion de dépendances, de temps par étape, de DAG

### Cooklang (.cook) — Le concurrent le plus sérieux

- Format texte lisible : `@ingredient{qty%unit}`, `#cookware`, `~{time}`
- Écosystème riche : CLI, apps iOS/Android/macOS, plugins VS Code, Obsidian
- **Fédération décentralisée** : tu héberges tes `.cook` sur ton blog/GitHub, la fédération indexe
- Recherche par tags, difficulté, ingrédients sur recipes.cooklang.org
- Philosophie "plain text > database" (Git-friendly, pérenne)
- **MAIS** : pas de notion de graphe de dépendances, pas d'enrichissement nutritionnel, pas de DAG, pas de parallélisme. C'est du texte structuré, pas un graphe

### RecipeML (2000), CookML, REML

- Formats XML historiques, largement abandonnés
- RecipeML supportait la conversion d'unités
- CookML avait des codes ingrédients (BLS allemand)
- **Tous morts ou en maintenance minimale**

### BBC Food Ontology

- RDF/linked data, créé en 2014
- Modèle sémantique riche (relations entre recettes, ingrédients, occasions, régimes)
- **Abandonné** quand la BBC a fermé BBC Food en 2018

---

## 4. Les APIs commerciales

### Spoonacular

- 360 000+ recettes, 86 000 produits alimentaires
- API puissante (recherche par ingrédients, nutrition, régime, allergies)
- **Payant** : gratuit limité (50 points/jour), puis 29-300$/mois
- Se dit "open source recipe database" mais les données ne sont pas vraiment ouvertes

### Edamam

- ~1M aliments, 790K UPC
- NLP + reconnaissance d'images
- 14-299$/mois
- Propriétaire

**Verdict** : les APIs commerciales ont de la donnée, mais elle est fermée, payante, et non-structurée au niveau des étapes (pas de DAG).

---

## 5. La recherche académique

### FoodKG (foodkg.github.io) — Le plus ambitieux

- Knowledge graph RDF : **63 millions de triples**
- Fusionne Recipe1M (recettes), USDA (nutrition), FoodOn (ontologie alimentaire)
- SPARQL endpoint public
- Supporte les requêtes en langage naturel ("quels plats indiens avec du poulet et de l'ail ?")
- **MAIS** : orienté recherche, pas d'UX, pas de communauté de contributeurs, pas de structuration des étapes

### English Recipe Flow Graph Corpus

- **300 recettes annotées avec des graphes de dépendances** (étapes, outils, ingrédients, produits intermédiaires)
- Parsing automatique : 71-87% F1 score
- C'est le modèle DAG appliqué aux recettes, en version académique

### MM-ReS Dataset

- **9 850 recettes avec des workflow graphs** annotés par des humains
- Multi-modal (texte + images)
- Modèles neural encoder-decoder pour construire les graphes automatiquement
- Performance : +20% vs baselines manuelles

### CookingSense (2024)

- Base de connaissances culinaires multi-disciplinaire
- FoodBench : benchmark pour évaluer les systèmes d'aide à la cuisine
- Améliore les LLM via RAG

### Swiss Food Knowledge Graph (2025)

- Intègre recettes, substitutions, nutriments, restrictions, guidelines suisses
- Pipeline d'enrichissement par LLM
- Graph-RAG pour des recommandations personnalisées

### PizzaCommonSense (EMNLP 2024)

- Dataset de raisonnement de sens commun sur les étapes intermédiaires de cuisson
- Inputs/outputs de chaque étape annotés
- **GPT-4 n'a que 26% de préférence humaine** — montre la difficulté du raisonnement culinaire procédural

### Recipe2Plan (EMNLP 2025)

- Benchmark de planification de tâches parallèles en cuisine avec contraintes temporelles
- **Les modèles SOTA galèrent** : ils sur-parallélisent et violent les contraintes temporelles
- Code open source : github.com/WilliamZR/Recipe2Plan

### NHK Recipe Dataset (2025)

- Dataset japonais avec annotations d'états d'ingrédients (cru → cuit → caramélisé)
- Modèle de suivi de transformation des ingrédients
- Llama3.1-70B et Qwen2.5-72B montrent de bonnes performances

**Verdict** : la recherche a prouvé que les graphes de dépendances de recettes fonctionnent et sont extractibles automatiquement. Mais **aucun de ces projets n'a produit un outil utilisable par le grand public**.

---

## 6. Les communs alimentaires (modèles d'inspiration)

### Open Food Facts — LE modèle à suivre

- 1,7M+ produits, 25 000+ contributeurs, 150 pays
- Données ouvertes (ODbL), API gratuite, dumps complets
- Association à but non-lucratif
- Scannes un code-barre → tu contribues
- **Succès car contribuer est trivial** (une photo) et la donnée est immédiatement utile (Yuka, etc.)

### Open Food Network

- Logiciel open source pour vendre de la nourriture locale
- 2 500+ entreprises, 20+ pays
- Gouvernance en commun, modèle commons-based peer production
- Membre du Data Food Consortium (standards d'interopérabilité alimentaire)

### Cookpad (commercial, non-ouvert)

- La plus grosse plateforme communautaire de recettes au monde
- Millions d'utilisateurs, multilingue, UGC + "cooksnaps"
- **Propriétaire, fermé, aucune donnée ouverte**

---

## 7. Les ressources Hugging Face exploitables

### Datasets

| Dataset | ID HuggingFace | Taille | Contenu | Utilité |
|---------|----------------|--------|---------|---------|
| RecipeNLG | `mbien/recipe_nlg` | **2.2M recettes** | Titre, ingrédients, étapes, NER | Base massive pour validation statistique |
| All Recipes | `corbt/all-recipes` | **2.15M recettes** | Ingrédients + directions | Cross-check statistique |
| CoT Reasoning Cooking | `mattwesney/CoT_Reasoning_Cooking` | 1-10K Q/A | Chain-of-thought culinaire | **Skills pour le vérificateur LLM** |
| Ingredients Alternatives | `Thefoodprocessor/ingredients_alternatives` | 74.5K | Substitutions d'ingrédients mappées | Enrichissement substitutions |
| Recipe with Features | `Thefoodprocessor/recipe_new_with_features_full` | 74.5K | Allergies, régimes, cuisines, vins | Enrichissement metadata |
| Food NER 1M | `HumbleIntelligence/food-ner-1-Million` | 1M+ lignes | Annotations IOB d'ingrédients | Entraîner un NER ingrédients |
| Cooking Recipes | `CodeKapital/CookingRecipes` | 2.23M | Ingrédients, directions, NER | Source additionnelle |
| NHK Recipe | `mashi6n/nhkrecipe-100-anno-1` | ~100 | États d'ingrédients annotés | Modèle de transformation d'états |

### Modèles spécialisés

| Modèle | ID HuggingFace | Fonction | Performance |
|--------|----------------|----------|-------------|
| Recipe Ingredient NER | `edwardjross/xlm-roberta-base-finetuned-recipe-all` | Parse ingrédient → nom, quantité, unité, état, température | **F1 = 0.967** |
| RecipeBERT | `alexdseo/RecipeBERT` | Embeddings culinaires (similarité de recettes) | Entraîné sur Recipe1M+ |
| FDA Nutrition NER | `sgarbi/bert-fda-nutrition-ner` | Extraction entités nutritionnelles | Spécialisé FDA |
| Nutrition Extractor | `openfoodfacts/nutrition-extractor` | OCR → tableaux nutritionnels | **F1 = 0.96** |
| T5 Recipe Generation | `flax-community/t5-recipe-generation` | Génère recettes à partir d'ingrédients | Génératif |

### Datasets académiques complémentaires (pas sur HF mais ouverts)

| Dataset | Source | Contenu | Importance |
|---------|--------|---------|------------|
| English Recipe Flow Graph Corpus | ACL 2020 | 300 recettes avec DAG complet annoté | Gold standard pour évaluer la structuration |
| MM-ReS | Académique | 9 850 recettes avec workflow graphs | Plus gros dataset de DAGs de recettes |
| GISMo | Facebook Research | KG de substitution d'ingrédients contextuelle | Substitutions intelligentes |
| Recipe2Plan | GitHub (EMNLP 2025) | Benchmark de planification parallèle | Tester la faisabilité temporelle du DAG |
| PizzaCommonSense | EMNLP 2024 | Raisonnement sens commun étapes intermédiaires | Benchmark de vérification |
| FoodKG | RPI | 63M triples RDF (recettes + nutrition + ontologie) | Knowledge graph de référence |

---

## 8. Stratégie de vérification LLM en 2026

### État de l'art des techniques de vérification

| Technique | Papier/Framework | Principe | Applicabilité recettes |
|-----------|-----------------|----------|----------------------|
| Multi-agent debate | MAD-Fact, FACT-AUDIT | LLMs adverses débattent pour converger vers la vérité | Moyen — bon pour les faits, moins pour les jugements culinaires subjectifs |
| Self-consistency sampling | Classique | N générations, on compare les convergences | Détecte la variance mais pas le biais systématique |
| Graph of Verification (GoV) | HuggingFace paper 2025 | Vérification en DAG, chaque noeud vérifié avec ses prémisses | **Très bon** — directement applicable à notre DAG |
| Constraint Satisfaction (Eidoku) | 2025 | Reformule la vérification en CSP (graphe + logique + features) | **Excellent** — vérification structurelle formelle |
| Self-Debating | EMNLP 2025 | Explications contrastives + jugement de cohérence | +5-10% F1 sur détection hallucinations |
| KG-grounded verification | Adjudicator (déc. 2025) | Council of Agents + Knowledge Graphs | **F1 = 0.99** sur vérification de labels |
| Proof-Carrying Numbers (PCN) | 2025 | Vérification mécanique des valeurs numériques | Applicable aux temps et quantités |
| Hybrid human-LLM | Science Direct 2025 | LLM + humain dans la boucle | +12% précision, -5% recall vs LLM seul |

### Pipeline de vérification recommandé

```
Source (URL/texte/image)
       │
       ▼
┌─────────────────────────────────────────┐
│  ÉTAPE 1 : Génération                   │
│  Claude Opus 4.5 + structured output    │
│  + prompt enrichi CoT_Reasoning_Cooking │
│  → DAG brut (JSON, schema garanti)      │
└──────────────────┬──────────────────────┘
                   │
       ┌───────────┼───────────┬──────────────┬──────────────┐
       ▼           ▼           ▼              ▼              ▼
┌────────────┐┌──────────┐┌───────────┐┌───────────┐┌──────────────┐
│ ÉTAPE 2a   ││ ÉTAPE 2b ││ ÉTAPE 2c  ││ ÉTAPE 2d  ││ ÉTAPE 2e     │
│ Vérif      ││ Cross-   ││ Grounding ││ Expert    ││ Plausibilité │
│ formelle   ││ check    ││ vs source ││ culinaire ││ statistique  │
│ (code)     ││ NER      ││ (Claude)  ││ (Claude)  ││ (4M recettes)│
│            ││ (F1=0.97)││           ││           ││              │
│ • Acyclique││ • Parse  ││ • Hallu-  ││ • Temps   ││ • Quantités  │
│ • Refs ok  ││   chaque ││   cinations││  suspects ││   dans les   │
│ • Unités   ││   ingré- ││ • Omis-   ││ • Ordre   ││   bornes ?   │
│ • Bornes   ││   dient  ││   sions   ││ • Tech-   ││ • Temps      │
│   temps    ││ • Compare││ • Distor- ││   niques  ││   cohérents  │
│ • Graphe   ││   vs LLM ││   sions   ││ • Quanti- ││   vs recettes│
│   connexe  ││          ││           ││   tés     ││   similaires?│
└─────┬──────┘└────┬─────┘└─────┬─────┘└─────┬─────┘└──────┬───────┘
      │            │            │             │             │
      └────────────┴────────────┴──────┬──────┴─────────────┘
                                       ▼
                            ┌─────────────────────┐
                            │  Score de confiance  │
                            │  composite (0-100%)  │
                            │  + rapport détaillé  │
                            │  par axe de vérif    │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │  TIER DE QUALITÉ     │
                            │  Draft / Reviewed /  │
                            │  Community-validated │
                            └─────────────────────┘
```

### Ce qui est vérifiable et ce qui ne l'est pas

| Type de vérification | Méthode | Fiabilité estimée | Automatisable ? |
|---------------------|---------|-------------------|-----------------|
| DAG structurellement valide | Code (topological sort, ref check) | **100%** | Oui, déterministe |
| Ingrédients = source | Grounding LLM + NER cross-check | **~97-99%** | Oui |
| Étapes = source (rien oublié/inventé) | Grounding LLM | **~95-97%** | Oui |
| Unités cohérentes | Règles formelles (mapping unité/catégorie) | **~99%** | Oui, déterministe |
| Temps dans des bornes réalistes | Bornes statistiques par technique | **~98%** | Oui, déterministe |
| Temps précisément corrects | Expert LLM + cross-check 4M recettes | **~85-90%** | Oui, mais faillible |
| Ordre des étapes culinairement correct | Expert LLM avec CoT culinaire | **~85-92%** | Oui, mais faillible |
| Parallélisations valides | Expert LLM + Recipe2Plan-style check | **~80-88%** | Oui, mais faillible |
| Nuances culinaires préservées | Expert LLM | **~70-80%** | Partiellement |
| Cohérence culturelle | Expert LLM | **~75-85%** | Partiellement |
| Quantités correctes pour les portions | Cross-check statistique | **~88-93%** | Oui |

### Estimation du taux d'erreur résiduel

| Type d'erreur | Sans pipeline de vérif | Avec pipeline complet | Gain |
|--------------|----------------------|----------------------|------|
| Ingrédient oublié/inventé | ~15% | **< 1%** | ~15x |
| DAG cassé structurellement | ~10% | **0%** | ∞ |
| Temps aberrant | ~3% | **~0%** | ∞ |
| Temps imprécis | ~30% | **~8-12%** | ~3x |
| Mauvaise dépendance | ~20% | **~5-8%** | ~3x |
| Unité/quantité incohérente | ~8% | **< 0.5%** | ~16x |
| Nuance culinaire perdue | ~40% | **~15-20%** | ~2x |
| **Erreur résiduelle globale** | **~25-35%** | **~10-15%** | **~2.5x** |

### Ce qui reste fondamentalement invérifiable par un LLM

1. **La recette source est elle-même fausse** — si le blog dit "200g de beurre pour une vinaigrette" et que c'est l'intention de l'auteur
2. **Les variations régionales légitimes** — couscous marocain vs algérien vs tunisien : l'ordre diffère, les épices diffèrent
3. **Le goût** — "saler à convenance", "un bon trait d'huile" : la normalisation tue l'intention
4. **Les recettes innovantes** — un chef qui fait volontairement quelque chose de "faux" sera flaggé à tort

---

## 9. Synthèse : le trou dans le marché

| Dimension | Ce qui existe | Ce qui manque |
|-----------|--------------|---------------|
| **Données structurées** | Schema.org (plat), Cooklang (texte enrichi) | DAG avec dépendances, parallélisme, états intermédiaires |
| **Enrichissement** | Spoonacular/Edamam (payant, fermé) | Nutrition, saisonnalité, régime — **ouvert** |
| **Graphe de recettes** | FoodKG (académique), Flow Graph Corpus (300 recettes) | **Accessible au grand public** avec UX |
| **Fédération** | Cooklang (texte plat indexé) | Données **riches et exploitables** (pas juste du texte) |
| **Commun ouvert** | Open Food Facts (produits, pas recettes), Wikibooks (mort) | **Recettes structurées ouvertes** |
| **Import automatique** | Tandoor/Mealie (import web basique) | Import URL/texte/image + **structuration LLM en DAG** |
| **UX de cuisson** | Aucun projet open/communautaire | Mode cuisson, Gantt, scaling, cochage |
| **Vérification** | Aucun système de vérification de recettes structurées | Pipeline multi-agent + validation formelle + cross-check statistique |

### Observations clés

1. **Le "Wikipedia des recettes" a été tenté et a échoué** (Wikibooks) — le texte brut n'apporte rien vs un blog
2. **Les graphes de dépendances existent en recherche** (300-9850 recettes) mais jamais en produit public
3. **Cooklang est le plus proche concurrent** mais reste du texte, pas un graphe. Pas de parallélisme, pas d'enrichissement
4. **Open Food Facts a prouvé le modèle communautaire** pour l'alimentaire — personne ne l'a fait pour les recettes structurées
5. **Toutes les APIs commerciales** ont de la donnée fermée et non-structurée au niveau des étapes
6. **4M+ recettes sont disponibles sur HF** pour le cross-check statistique
7. **Des modèles NER spécialisés existent** (F1 = 0.967) pour valider le parsing d'ingrédients
8. **Le chain-of-thought culinaire existe** (CoT_Reasoning_Cooking) comme "skill" de vérification

---

## 10. Recommandation : le modèle "commun décentralisé"

### Vision

> Un commun numérique de recettes structurées en graphes de dépendances, enrichies en nutrition et saisonnalité, construites et améliorées par la communauté, ouvertes à tous.

### Pourquoi ça marcherait (contrairement aux tentatives précédentes)

| Tentative passée | Pourquoi ça a échoué | Ce qu'on fait différemment |
|-----------------|---------------------|---------------------------|
| Wikibooks Cookbook | Texte brut = pas de valeur ajoutée | DAG structuré = UX de cuisson impossible ailleurs |
| OpenRecipes | Juste des métadonnées, pas d'UX | App complète (cuisson, Gantt, scaling, meal plan) |
| Cooklang Federation | Texte enrichi mais pas de graphe | Graphe de dépendances + enrichissement auto |
| TheMealDB | 599 recettes, qualité basse | Pipeline LLM + vérification multi-agent |

### Le cycle de contribution

```
Contributeur colle une URL
         │
         ▼
LLM structure automatiquement (10 sec)
         │
         ▼
Pipeline de vérification (5 passes)
         │
         ▼
Score de confiance affiché
         │
         ▼
Contributeur vérifie/corrige (5 min)
         │
         ▼
Base ouverte (CC BY-SA / ODbL)
         │
         ▼
Utilisateurs cuisinent avec l'app
         │
         ▼
Feedback implicite (temps réels, étapes sautées, corrections)
         │
         ▼
Donnée s'améliore progressivement
```

### Tiers de qualité

| Tier | Condition | Affichage |
|------|-----------|-----------|
| **Draft** | Générée par LLM, vérification automatique passée | Bandeau "non vérifiée par un humain" |
| **Reviewed** | Un humain a vérifié/corrigé | Badge "vérifiée" |
| **Community-validated** | Cuisinée N fois, temps convergent, aucun signalement | Badge "validée par la communauté" |

### API ouverte

```
GET  /api/v1/recipes                         — Catalogue
GET  /api/v1/recipes/{id}                    — Recette structurée (DAG complet)
GET  /api/v1/recipes/{id}/graph              — Le DAG seul
GET  /api/v1/recipes/{id}/confidence         — Score de confiance détaillé
GET  /api/v1/recipes/search?q=...            — Recherche
GET  /api/v1/ingredients/{id}/substitutions   — Substitutions
GET  /api/v1/ingredients/{id}/pairings       — Associations
GET  /api/v1/seasonal?month=3&region=fr      — Produits de saison
GET  /api/v1/export/full                     — Dump complet
```

### Modèle de financement (sans trahir le commun)

| Source | Modèle |
|--------|--------|
| Dons | Patreon, Open Collective, fondations |
| Grants | Fondations open data, santé publique, alimentation durable |
| API premium | Rate limits généreux en gratuit, SLA + support pour entreprises |
| Partenariats | Apps commerciales qui utilisent les données |

### Ce qui est réaliste vs ce qui est du bullshit

**Réaliste :**
- Pipeline de structuration + vérification à ~85-90% de fiabilité
- Contribution facilitée (coller une URL = contribuer)
- Feedback loop via le mode cuisson
- Communauté de correction incrémentale

**Difficile mais faisable :**
- Atteindre une masse critique de contributeurs
- Maintenir la qualité à l'échelle
- Résister à la tentation de fermer les données

**Bullshit (ne pas prétendre) :**
- Que les recettes générées sont "parfaites"
- Que le LLM remplace un chef
- Que la vérification automatique suffit seule

---

> **Conclusion** : le projet est viable et comble un vide réel. Le positionnement est entre Open Food Facts (modèle communautaire), Cooklang (format ouvert), et FoodKG (graphe), avec une UX de cuisson que personne n'a. La clé du succès sera la transparence sur la qualité des données et la facilité de contribution.
