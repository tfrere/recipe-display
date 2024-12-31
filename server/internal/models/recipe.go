package models

import "strings"

// Recipe représente la structure de données interne
type Recipe struct {
	Metadata struct {
		Title       string `json:"title"`
		Description string `json:"description"`
		Servings    int    `json:"servings"`
		Difficulty  string `json:"difficulty"`
		TotalTime   string `json:"totalTime"`
		Image       string `json:"image"`
		ImageUrl    string `json:"imageUrl"`
		SourceUrl   string `json:"sourceUrl"`
		Diet        string `json:"diet"`
		Season      string `json:"season"`
		RecipeType  string `json:"recipeType"`
		Quick       bool   `json:"quick"`
		Notes       string `json:"notes"`
	} `json:"metadata"`
	IngredientsList []struct {
		ID       string `json:"id"`
		Name     string `json:"name"`
		Unit     string `json:"unit"`
		Category string `json:"category"`
		State    string `json:"state"`
	} `json:"ingredientsList"`
	SubRecipes []struct {
		ID          string `json:"id"`
		Title       string `json:"title"`
		Ingredients map[string]struct {
			Amount float64 `json:"amount"`
			State  string  `json:"state"`
		} `json:"ingredients"`
		Steps []struct {
			ID     string `json:"id"`
			Action string `json:"action"`
			Time   string `json:"time"`
			Tools  []string `json:"tools"`
			Inputs []struct {
				Type string `json:"type"`
				Ref  string `json:"ref"`
			} `json:"inputs"`
			Output struct {
				State       string `json:"state"`
				Description string `json:"description"`
			} `json:"output"`
		} `json:"steps"`
	} `json:"subRecipes"`
}

// UIRecipe représente la structure de données pour le front-end
type UIRecipe struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Servings    int    `json:"servings"`
	Difficulty  string `json:"difficulty"`
	TotalTime   string `json:"totalTime"`
	Image       string `json:"image"`
	ImageUrl    string `json:"imageUrl"`
	SourceUrl   string `json:"sourceUrl"`
	Diet        string `json:"diet"`
	Season      string `json:"season"`
	RecipeType  string `json:"recipeType"`
	Quick       bool   `json:"quick"`
	Notes       string `json:"notes"`
	Slug        string `json:"slug"`
	Ingredients map[string]struct {
		Name     string `json:"name"`
		Unit     string `json:"unit"`
		Category string `json:"category"`
		State    string `json:"state"`
	} `json:"ingredients"`
	SubRecipes map[string]struct {
		Title string `json:"title"`
		Ingredients map[string]struct {
			Amount float64 `json:"amount"`
			State  string  `json:"state"`
		} `json:"ingredients"`
		Steps []struct {
			ID     string `json:"id"`
			Type   string `json:"type"`
			Action string `json:"action"`
			Time   string `json:"time"`
			Tools  []string `json:"tools"`
			Inputs []struct {
				Type string `json:"type"`
				Ref  string `json:"ref"`
			} `json:"inputs"`
			Output struct {
				State       string `json:"state"`
				Description string `json:"description"`
			} `json:"output"`
		} `json:"steps"`
	} `json:"subRecipes"`
}

// ConvertToUIRecipe convertit une Recipe en UIRecipe
func (r *Recipe) ConvertToUIRecipe() *UIRecipe {
	ui := &UIRecipe{
		Title:       r.Metadata.Title,
		Description: r.Metadata.Description,
		Servings:    r.Metadata.Servings,
		Difficulty:  r.Metadata.Difficulty,
		TotalTime:   r.Metadata.TotalTime,
		Image:       r.Metadata.Image,
		ImageUrl:    r.Metadata.ImageUrl,
		SourceUrl:   r.Metadata.SourceUrl,
		Diet:        r.Metadata.Diet,
		Season:      r.Metadata.Season,
		RecipeType:  r.Metadata.RecipeType,
		Quick:       r.Metadata.Quick,
		Notes:       r.Metadata.Notes,
		Slug:        strings.ToLower(strings.ReplaceAll(r.Metadata.Title, " ", "-")),
		Ingredients: make(map[string]struct {
			Name     string `json:"name"`
			Unit     string `json:"unit"`
			Category string `json:"category"`
			State    string `json:"state"`
		}),
		SubRecipes: make(map[string]struct {
			Title string `json:"title"`
			Ingredients map[string]struct {
				Amount float64 `json:"amount"`
				State  string  `json:"state"`
			} `json:"ingredients"`
			Steps []struct {
				ID     string `json:"id"`
				Type   string `json:"type"`
				Action string `json:"action"`
				Time   string `json:"time"`
				Tools  []string `json:"tools"`
				Inputs []struct {
					Type string `json:"type"`
					Ref  string `json:"ref"`
				} `json:"inputs"`
				Output struct {
					State       string `json:"state"`
					Description string `json:"description"`
				} `json:"output"`
			} `json:"steps"`
		}),
	}

	// Convertir les ingrédients
	for _, ingredient := range r.IngredientsList {
		ui.Ingredients[ingredient.ID] = struct {
			Name     string `json:"name"`
			Unit     string `json:"unit"`
			Category string `json:"category"`
			State    string `json:"state"`
		}{
			Name:     ingredient.Name,
			Unit:     ingredient.Unit,
			Category: ingredient.Category,
			State:    ingredient.State,
		}
	}

	// Remplir les sous-recettes
	for _, subRecipe := range r.SubRecipes {
		steps := make([]struct {
			ID     string `json:"id"`
			Type   string `json:"type"`
			Action string `json:"action"`
			Time   string `json:"time"`
			Tools  []string `json:"tools"`
			Inputs []struct {
				Type string `json:"type"`
				Ref  string `json:"ref"`
			} `json:"inputs"`
			Output struct {
				State       string `json:"state"`
				Description string `json:"description"`
			} `json:"output"`
		}, len(subRecipe.Steps))

		// Copier les étapes
		for i, step := range subRecipe.Steps {
			steps[i] = struct {
				ID     string `json:"id"`
				Type   string `json:"type"`
				Action string `json:"action"`
				Time   string `json:"time"`
				Tools  []string `json:"tools"`
				Inputs []struct {
					Type string `json:"type"`
					Ref  string `json:"ref"`
				} `json:"inputs"`
				Output struct {
					State       string `json:"state"`
					Description string `json:"description"`
				} `json:"output"`
			}{
				ID:     step.ID,
				Type:   "",  // Type vide par défaut
				Action: step.Action,
				Time:   step.Time,
				Tools:  step.Tools,
				Inputs: step.Inputs,
				Output: step.Output,
			}
		}

		// Créer la sous-recette
		ui.SubRecipes[subRecipe.ID] = struct {
			Title string `json:"title"`
			Ingredients map[string]struct {
				Amount float64 `json:"amount"`
				State  string  `json:"state"`
			} `json:"ingredients"`
			Steps []struct {
				ID     string `json:"id"`
				Type   string `json:"type"`
				Action string `json:"action"`
				Time   string `json:"time"`
				Tools  []string `json:"tools"`
				Inputs []struct {
					Type string `json:"type"`
					Ref  string `json:"ref"`
				} `json:"inputs"`
				Output struct {
					State       string `json:"state"`
					Description string `json:"description"`
				} `json:"output"`
			} `json:"steps"`
		}{
			Title: subRecipe.Title,
			Ingredients: subRecipe.Ingredients, // Utiliser directement la map d'ingrédients existante
			Steps: steps,
		}
	}

	return ui
}

// Helper functions
func determineCategory(name string) string {
	name = strings.ToLower(name)
	switch {
	case strings.Contains(name, "farine"):
		return "farine"
	case strings.Contains(name, "sucre"):
		return "sucre"
	case strings.Contains(name, "œuf") || strings.Contains(name, "oeuf"):
		return "œuf"
	case strings.Contains(name, "lait") || strings.Contains(name, "crème") || strings.Contains(name, "beurre") || strings.Contains(name, "yaourt"):
		return "produit-laitier"
	case strings.Contains(name, "chocolat"):
		return "chocolat"
	case strings.Contains(name, "noix") || strings.Contains(name, "amande") || strings.Contains(name, "noisette") || strings.Contains(name, "pistache"):
		return "fruit-sec"
	case strings.Contains(name, "épice") || strings.Contains(name, "cannelle") || strings.Contains(name, "vanille") || strings.Contains(name, "muscade"):
		return "épices"
	default:
		return "autres"
	}
}

// GenerateRecipeRequest représente la requête pour générer une recette
type GenerateRecipeRequest struct {
	Source string `json:"source"`
}
