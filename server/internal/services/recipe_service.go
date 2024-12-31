package services

import (
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"recipe-display/server/internal/models"
	"recipe-display/server/internal/utils"
	recipegenerator "recipe-display/server/pkg/recipe-generator"
)

type RecipeService struct {
	dataDir string
}

type RecipeListItem struct {
	Title       string   `json:"title"`
	Slug        string   `json:"slug"`
	Metadata    Metadata `json:"metadata"`
	Ingredients []string `json:"ingredients"`
	Diet        string   `json:"diet"`
}

type Metadata struct {
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
		var diet = "normal"      // Default value
		var season = "spring"    // Default value
		var recipeType = "main"  // Default value
		var quick = false        // Default value

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
			if d, ok := metadata["diet"].(string); ok {
				diet = d
			}
			if s, ok := metadata["season"].(string); ok {
				season = s
			}
			if t, ok := metadata["recipeType"].(string); ok {
				recipeType = t
			}
			if q, ok := metadata["quick"].(bool); ok {
				quick = q
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
			"diet":        diet,
			"season":      season,
			"recipeType":  recipeType,
			"quick":       quick,
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

		// Get title and create metadata
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
			// Ensure metadata exists in recipe
			if _, ok := recipe["metadata"]; !ok {
				metadata := map[string]interface{}{
					"description": recipe["description"],
					"servings":    recipe["servings"],
					"difficulty":  recipe["difficulty"],
					"totalTime":   recipe["totalTime"],
					"image":       recipe["image"],
					"imageUrl":    recipe["imageUrl"],
					"sourceUrl":   recipe["sourceUrl"],
					"diet":        recipe["diet"],
					"season":      recipe["season"],
					"recipeType":  recipe["recipeType"],
					"quick":       recipe["quick"],
				}
				recipe["metadata"] = metadata
			}
			
			// Convert back to JSON string
			resultJSON, err := json.Marshal(recipe)
			if err != nil {
				return "", fmt.Errorf("failed to marshal recipe: %v", err)
			}
			return string(resultJSON), nil
		}
	}

	return "", fmt.Errorf("recipe with slug %s not found", slug)
}

func (s *RecipeService) GetRecipeList() ([]RecipeListItem, error) {
	files, err := ioutil.ReadDir(s.dataDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read data directory: %v", err)
	}

	var items []RecipeListItem
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

		var recipe models.Recipe
		if err := json.Unmarshal(recipeData, &recipe); err != nil {
			log.Printf("ERROR: Could not parse recipe file %s: %v", file.Name(), err)
			continue
		}

		// Extraire les noms des ingrédients
		ingredients := make([]string, 0, len(recipe.IngredientsList))
		for _, ing := range recipe.IngredientsList {
			ingredients = append(ingredients, ing.Name)
		}

		// Créer l'item de liste
		item := RecipeListItem{
			Title: recipe.Metadata.Title,
			Slug:  s.GenerateSlug(recipe.Metadata.Title),
			Metadata: Metadata{
				Description: recipe.Metadata.Description,
				Servings:    recipe.Metadata.Servings,
				Difficulty:  recipe.Metadata.Difficulty,
				TotalTime:   recipe.Metadata.TotalTime,
				Image:       recipe.Metadata.Image,
				ImageUrl:    recipe.Metadata.ImageUrl,
				SourceUrl:   recipe.Metadata.SourceUrl,
				Diet:        recipe.Metadata.Diet,
				Season:      recipe.Metadata.Season,
				RecipeType:  recipe.Metadata.RecipeType,
				Quick:       recipe.Metadata.Quick,
			},
			Ingredients: ingredients,
		}
		items = append(items, item)
	}

	return items, nil
}

func (s *RecipeService) findRecipeBySourceUrl(sourceUrl string) (bool, error) {
	files, err := ioutil.ReadDir(s.dataDir)
	if err != nil {
		return false, fmt.Errorf("failed to read data directory: %v", err)
	}

	for _, file := range files {
		if file.IsDir() || !strings.HasSuffix(file.Name(), ".recipe.json") || file.Name() == "recipe.schema.json" {
			continue
		}

		filePath := filepath.Join(s.dataDir, file.Name())
		recipeData, err := ioutil.ReadFile(filePath)
		if err != nil {
			continue
		}

		var recipe models.Recipe
		if err := json.Unmarshal(recipeData, &recipe); err != nil {
			continue
		}

		if recipe.Metadata.SourceUrl == sourceUrl {
			return true, nil
		}
	}

	return false, nil
}

func (s *RecipeService) AddRecipeFromUrl(urlString string) (*map[string]interface{}, error) {
	// Vérifier si la recette existe déjà
	exists, err := s.findRecipeBySourceUrl(urlString)
	if err != nil {
		return nil, fmt.Errorf("failed to check for existing recipe: %v", err)
	}
	if exists {
		return nil, fmt.Errorf("recipe already exists")
	}

	// Créer un dossier temporaire pour les opérations
	tempDir, err := os.MkdirTemp("", "recipe-*")
	if err != nil {
		return nil, fmt.Errorf("failed to create temp directory: %v", err)
	}
	defer os.RemoveAll(tempDir) // Nettoyer le dossier temporaire à la fin

	// Récupérer le contenu de la page
	content, err := utils.FetchWebPageContent(urlString)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch URL content: %v", err)
	}

	// Extraire le contenu pertinent du HTML
	webContent, err := utils.ExtractWebContent(content)
	if err != nil {
		return nil, fmt.Errorf("failed to extract web content: %v", err)
	}

	// Générer la recette
	generator := recipegenerator.NewRecipeGenerator()
	recipe, err := generator.GenerateFromWebContent(webContent, urlString, webContent.ImageURLs)
	if err != nil {
		return nil, fmt.Errorf("failed to generate recipe: %v", err)
	}

	// Générer le slug
	slug := s.GenerateSlug(recipe.Metadata.Title)
	recipe.Metadata.Image = fmt.Sprintf("%s.jpg", slug)

	// S'assurer que l'URL de l'image a un protocole
	if recipe.Metadata.ImageUrl != "" {
		if !strings.HasPrefix(recipe.Metadata.ImageUrl, "http://") && !strings.HasPrefix(recipe.Metadata.ImageUrl, "https://") {
			// Si l'URL commence par //, ajouter https:
			if strings.HasPrefix(recipe.Metadata.ImageUrl, "//") {
				recipe.Metadata.ImageUrl = "https:" + recipe.Metadata.ImageUrl
			} else if strings.HasPrefix(recipe.Metadata.ImageUrl, "/") {
				// Si l'URL est absolue, ajouter le domaine
				sourceURL, err := url.Parse(urlString)
				if err == nil {
					recipe.Metadata.ImageUrl = fmt.Sprintf("%s://%s%s", sourceURL.Scheme, sourceURL.Host, recipe.Metadata.ImageUrl)
				}
			} else {
				// Si l'URL est relative, la construire à partir de l'URL de base
				sourceURL, err := url.Parse(urlString)
				if err == nil {
					baseURL := fmt.Sprintf("%s://%s", sourceURL.Scheme, sourceURL.Host)
					if strings.HasSuffix(baseURL, "/") {
						recipe.Metadata.ImageUrl = baseURL + recipe.Metadata.ImageUrl
					} else {
						recipe.Metadata.ImageUrl = baseURL + "/" + recipe.Metadata.ImageUrl
					}
				}
			}
		}
	}

	// Télécharger l'image dans le dossier temporaire
	tempImagePath := filepath.Join(tempDir, recipe.Metadata.Image)
	if err := utils.DownloadFile(recipe.Metadata.ImageUrl, tempImagePath); err != nil {
		return nil, fmt.Errorf("failed to download image: %v", err)
	}

	// Convertir la recette en JSON
	jsonData, err := recipe.ToJSON()
	if err != nil {
		return nil, fmt.Errorf("failed to convert recipe to JSON: %v", err)
	}

	// Préparer les chemins finaux
	recipePath := filepath.Join(s.dataDir, fmt.Sprintf("%s.recipe.json", slug))
	imagePath := filepath.Join(s.dataDir, "images", "original", recipe.Metadata.Image)

	// Vérifier si la recette existe déjà
	if _, err := os.Stat(recipePath); err == nil {
		return nil, fmt.Errorf("recipe already exists: %s", slug)
	}

	// Créer le dossier images/original s'il n'existe pas
	imagesDir := filepath.Join(s.dataDir, "images", "original")
	if err := os.MkdirAll(imagesDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create images directory: %v", err)
	}

	// Copier l'image du dossier temporaire vers le dossier final
	srcFile, err := os.Open(tempImagePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open source image: %v", err)
	}
	defer srcFile.Close()

	dstFile, err := os.Create(imagePath)
	if err != nil {
		return nil, fmt.Errorf("failed to create destination image: %v", err)
	}
	defer dstFile.Close()

	if _, err := io.Copy(dstFile, srcFile); err != nil {
		return nil, fmt.Errorf("failed to copy image: %v", err)
	}

	// Sauvegarder la recette
	if err := os.WriteFile(recipePath, jsonData, 0644); err != nil {
		// Si l'écriture de la recette échoue, supprimer l'image
		os.Remove(imagePath)
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
		"diet":        recipe.Metadata.Diet,
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

// GenerateSlug génère un slug à partir d'un titre
func (s *RecipeService) GenerateSlug(title string) string {
	// Convertir en minuscules
	slug := strings.ToLower(title)
	
	// Remplacer les caractères spéciaux et espaces par des tirets
	slug = strings.Map(func(r rune) rune {
		switch {
		case r >= 'a' && r <= 'z':
			return r
		case r >= '0' && r <= '9':
			return r
		case r == ' ' || r == '-' || r == '_':
			return '-'
		case r == 'é' || r == 'è' || r == 'ê' || r == 'ë':
			return 'e'
		case r == 'à' || r == 'â' || r == 'ä':
			return 'a'
		case r == 'ù' || r == 'û' || r == 'ü':
			return 'u'
		case r == 'î' || r == 'ï':
			return 'i'
		case r == 'ô' || r == 'ö':
			return 'o'
		case r == 'ç':
			return 'c'
		default:
			return -1
		}
	}, slug)
	
	// Remplacer les multiples tirets par un seul
	slug = strings.Join(strings.FieldsFunc(slug, func(r rune) bool {
		return r == '-'
	}), "-")
	
	return slug
}
