package services

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"path/filepath"
	"strings"

	"recipe-display/server/internal/utils"
)

type RecipeService struct {
	dataDir string
}

func NewRecipeService(dataDir string) *RecipeService {
	log.Printf("Initializing RecipeService with data directory: %s", dataDir)
	return &RecipeService{
		dataDir: dataDir,
	}
}

func (s *RecipeService) GetAllRecipes() ([]map[string]interface{}, error) {
	files, err := ioutil.ReadDir(s.dataDir)
	if err != nil {
		log.Printf("ERROR: Failed to read data directory %s: %v", s.dataDir, err)
		return nil, fmt.Errorf("failed to read data directory: %v", err)
	}

	var recipes []map[string]interface{}
	for _, file := range files {
		if file.IsDir() || !strings.HasSuffix(file.Name(), ".recipe.json") || file.Name() == "recipe.schema.json" {
			continue
		}

		filePath := filepath.Join(s.dataDir, file.Name())
		recipeData, err := ioutil.ReadFile(filePath)
		if err != nil {
			log.Printf("ERROR: Could not read recipe file %s: %v", file.Name(), err)
			continue
		}

		var recipe map[string]interface{}
		if err := json.Unmarshal(recipeData, &recipe); err != nil {
			log.Printf("ERROR: Could not parse recipe file %s: %v", file.Name(), err)
			continue
		}

		// Get metadata from either format
		var title, description, image string
		var servings float64 = 4 // Default value
		var difficulty = "medium" // Default value
		var totalTime = "30min"  // Default value

		if metadata, ok := recipe["metadata"].(map[string]interface{}); ok {
			// New format with metadata
			if t, ok := metadata["title"].(string); ok {
				title = t
			}
			if d, ok := metadata["description"].(string); ok {
				description = d
			}
			if i, ok := metadata["image"].(string); ok {
				image = i
			}
			if s, ok := metadata["servings"].(float64); ok {
				servings = s
			}
			if d, ok := metadata["difficulty"].(string); ok {
				difficulty = d
			}
			if t, ok := metadata["totalTime"].(string); ok {
				totalTime = t
			}
		} else {
			// Old format
			title = filepath.Base(file.Name())
			title = strings.TrimSuffix(title, ".recipe.json")
			title = strings.ReplaceAll(title, "-", " ")
			title = strings.Title(strings.ToLower(title))
		}

		slug := utils.CreateSlug(title)
		recipes = append(recipes, map[string]interface{}{
			"title":       title,
			"description": description,
			"image":       image,
			"slug":        slug,
			"servings":    servings,
			"difficulty":  difficulty,
			"totalTime":   totalTime,
		})
	}

	return recipes, nil
}

func (s *RecipeService) FindRecipeBySlug(slug string) (string, error) {
	files, err := ioutil.ReadDir(s.dataDir)
	if err != nil {
		log.Printf("ERROR: Failed to read data directory %s: %v", s.dataDir, err)
		return "", fmt.Errorf("failed to read data directory: %v", err)
	}

	for _, file := range files {
		if file.IsDir() || !strings.HasSuffix(file.Name(), ".recipe.json") || file.Name() == "recipe.schema.json" {
			continue
		}

		filePath := filepath.Join(s.dataDir, file.Name())
		recipeData, err := ioutil.ReadFile(filePath)
		if err != nil {
			log.Printf("ERROR: Could not read recipe file %s: %v", file.Name(), err)
			continue
		}

		var recipe map[string]interface{}
		if err := json.Unmarshal(recipeData, &recipe); err != nil {
			log.Printf("ERROR: Could not parse recipe file %s: %v", file.Name(), err)
			continue
		}

		// Get title from either format
		var title string
		if metadata, ok := recipe["metadata"].(map[string]interface{}); ok {
			if t, ok := metadata["title"].(string); ok {
				title = t
			}
		} else {
			title = filepath.Base(file.Name())
			title = strings.TrimSuffix(title, ".recipe.json")
			title = strings.ReplaceAll(title, "-", " ")
			title = strings.Title(strings.ToLower(title))
		}

		if utils.CreateSlug(title) == slug {
			return string(recipeData), nil
		}
	}

	return "", fmt.Errorf("recipe with slug %s not found", slug)
}

// Fonctions utilitaires pour gérer les conversions de type
func getFloatValue(v interface{}) float64 {
	switch val := v.(type) {
	case float64:
		return val
	case int:
		return float64(val)
	default:
		return 0
	}
}

func getStringValue(v interface{}) string {
	if str, ok := v.(string); ok {
		return str
	}
	return ""
}
