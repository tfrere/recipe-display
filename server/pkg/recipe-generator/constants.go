package recipegenerator

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// Constants représente la structure des constantes partagées
type Constants struct {
	Seasons []struct {
		ID    string `json:"id"`
		Label string `json:"label"`
	} `json:"seasons"`
	RecipeTypes []struct {
		ID    string `json:"id"`
		Label string `json:"label"`
	} `json:"recipe_types"`
	Diets []struct {
		ID    string `json:"id"`
		Label string `json:"label"`
	} `json:"diets"`
	Units struct {
		Integer []string `json:"integer"`
		Weight  struct {
			Gram    []string          `json:"gram"`
			Display map[string]string `json:"display"`
		} `json:"weight"`
		Volume struct {
			Spoons     []string          `json:"spoons"`
			Containers []string          `json:"containers"`
			Display    map[string]string `json:"display"`
		} `json:"volume"`
	} `json:"units"`
	ScalingFactors map[string]float64 `json:"scaling_factors"`
	Ingredients    struct {
		Categories []struct {
			ID    string `json:"id"`
			Label string `json:"label"`
		} `json:"categories"`
	} `json:"ingredients"`
}

// loadConstants charge les constantes depuis le fichier shared/constants.json
func loadConstants() (*Constants, error) {
	// Trouver le chemin du fichier constants.json
	currentDir, err := os.Getwd()
	if err != nil {
		return nil, fmt.Errorf("error getting current directory: %v", err)
	}

	// Remonter jusqu'à trouver le dossier shared
	var constantsPath string
	for dir := currentDir; dir != "/"; dir = filepath.Dir(dir) {
		path := filepath.Join(dir, "shared", "constants.json")
		if _, err := os.Stat(path); err == nil {
			constantsPath = path
			break
		}
	}

	if constantsPath == "" {
		return nil, fmt.Errorf("constants.json not found in shared directory")
	}

	// Lire le fichier
	data, err := os.ReadFile(constantsPath)
	if err != nil {
		return nil, fmt.Errorf("error reading constants file: %v", err)
	}

	// Décoder le JSON
	var constants Constants
	if err := json.Unmarshal(data, &constants); err != nil {
		return nil, fmt.Errorf("error unmarshaling constants: %v", err)
	}

	return &constants, nil
}

// formatForTemplate formate les constantes pour le template
func (c *Constants) formatForTemplate() map[string]string {
	// Formater les IDs en chaînes séparées par des |
	formatIDs := func(items []struct {
		ID    string `json:"id"`
		Label string `json:"label"`
	}) string {
		if len(items) == 0 {
			return ""
		}
		result := items[0].ID
		for _, item := range items[1:] {
			result += "|" + item.ID
		}
		return result
	}

	return map[string]string{
		"Seasons":             formatIDs(c.Seasons),
		"RecipeTypes":        formatIDs(c.RecipeTypes),
		"DietTypes":          formatIDs(c.Diets),
		"IngredientCategories": formatIDs(c.Ingredients.Categories),
	}
}
