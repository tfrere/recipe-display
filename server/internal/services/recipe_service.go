package services

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strings"

	"recipe-display/server/internal/utils"
	recipegenerator "recipe-display/server/pkg/recipe-generator"
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

func (s *RecipeService) AddRecipeFromUrl(url string) (*map[string]interface{}, error) {
	// Créer un nouveau générateur de recettes
	generator := recipegenerator.NewRecipeGenerator()

	// Récupérer le contenu de la page web et générer la recette
	recipe, err := generator.GenerateFromWebContent("", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to generate recipe: %v", err)
	}

	// Créer le slug à partir du titre
	slug := utils.CreateSlug(recipe.Metadata.Title)

	// Préparer les chemins de fichiers
	imagePath := filepath.Join(s.dataDir, "images", "original", slug+filepath.Ext(recipe.Metadata.ImageUrl))
	recipePath := filepath.Join(s.dataDir, slug+".recipe.json")

	// Télécharger l'image si disponible
	if recipe.Metadata.ImageUrl != "" {
		if err := utils.DownloadFile(recipe.Metadata.ImageUrl, imagePath); err != nil {
			log.Printf("WARNING: Failed to download image: %v", err)
		} else {
			// Mettre à jour le chemin de l'image dans la recette
			recipe.Metadata.Image = slug + filepath.Ext(recipe.Metadata.ImageUrl)
		}
	}

	// Convertir la recette en JSON
	jsonData, err := recipe.ToJSON()
	if err != nil {
		return nil, fmt.Errorf("failed to convert recipe to JSON: %v", err)
	}

	// S'assurer que le dossier existe
	if err := os.MkdirAll(filepath.Dir(recipePath), 0755); err != nil {
		return nil, fmt.Errorf("failed to create directory: %v", err)
	}

	// Sauvegarder la recette
	if err := os.WriteFile(recipePath, jsonData, 0644); err != nil {
		return nil, fmt.Errorf("failed to save recipe: %v", err)
	}

	// Préparer la réponse
	response := map[string]interface{}{
		"title":       recipe.Metadata.Title,
		"description": recipe.Metadata.Description,
		"image":       recipe.Metadata.Image,
		"slug":        slug,
		"servings":    recipe.Metadata.Servings,
		"difficulty":  recipe.Metadata.Difficulty,
		"totalTime":   recipe.Metadata.TotalTime,
	}

	return &response, nil
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
