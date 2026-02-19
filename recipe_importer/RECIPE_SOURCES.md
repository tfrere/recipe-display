# Recipe Sources — Sites à scraper

## Critères de sélection

1. **Qualité des recettes** — Originales, testées par l'auteur, ingrédients précis avec quantités, instructions détaillées
2. **Structure du contenu** — Pages bien structurées (titre/ingrédients/étapes séparés), pas de paywall, URLs propres
3. **Orientation végétarienne** — Engagement réel, variété de cuisines et techniques, créativité
4. **Volume** — 100+ recettes minimum, contenu mis à jour régulièrement
5. **Légitimité** — Auteur identifié, cookbooks publiés, communauté active

## Tier S — Les incontournables

| Site | URL | Langue | Style | Volume | Status |
|---|---|---|---|---|---|
| Cookie and Kate | https://cookieandkate.com | EN | Végétarien whole food | ~1000 recettes | ✅ 2/2 OK |
| Love and Lemons | https://www.loveandlemons.com | EN | Végétarien méditerranéen | 800+ recettes | ✅ 2/2 OK |
| Smitten Kitchen | https://smittenkitchen.com | EN | Végétarien créatif | 374 recettes végé | ✅ 2/2 OK |
| 101 Cookbooks | https://www.101cookbooks.com | EN | Végétarien californien | 700+ recettes | ✅ 2/2 OK |
| Minimalist Baker | https://minimalistbaker.com | EN | Vegan simple | 800+ recettes | ✅ 2/2 OK |

## Tier A — Excellent, style distinct

| Site | URL | Langue | Style | Volume | Status |
|---|---|---|---|---|---|
| Oh She Glows | https://ohsheglows.com | EN | Vegan whole food | 500+ recettes | — |
| Vegan Richa | https://www.veganricha.com | EN | Vegan indien/fusion | 500+ recettes | — |
| Forks Over Knives | https://www.forksoverknives.com/recipes | EN | Vegan WFPB | 1000+ recettes | — |
| Free The Pickle | https://freethepickle.fr | FR | Végétarien saisonnier | 500+ recettes | Déjà importé |
| La Cuisine de Jean-Philippe | https://www.lacuisinedejeanphilippe.com | FR | Vegan québécois | 300+ recettes | — |

## Tier B — Très bon, niche

| Site | URL | Langue | Style | Volume | Status |
|---|---|---|---|---|---|
| Mail0ves | https://mailofaitmaison.com | FR | Vegan gourmand | 200+ recettes | — |
| France Végétalienne | https://francevegetalienne.fr | FR | Vegan régional français | 300+ recettes | — |
| Le Cul de Poule | https://leculdepoule.co | FR | Vegan accessible | 200+ recettes | — |
| Vegan Pratique | https://vegan-pratique.fr | FR | Vegan découverte | 900+ recettes | — |
| Green Cuisine | https://www.greencuisine.fr | FR | Végétarien sans gluten | 150+ recettes | — |
| The Veggie Table | https://www.theveggietable.com | EN | Végétarien français | 200+ recettes | — |

## Vérifications à faire avant import

- [ ] HTML scrapable par notre `web_scraper` (pas SPA, contenu dans le DOM)
- [ ] Format structuré JSON-LD / schema.org Recipe (bonus)
- [ ] robots.txt autorise le scraping
- [ ] Test de 2-3 recettes dans notre pipeline complet
- [ ] Pas de paywall / login obligatoire
