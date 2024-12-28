package recipegenerator

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"recipe-display/server/internal/utils"

	"github.com/rs/zerolog/log"
	"github.com/xeipuuv/gojsonschema"
)

// Recipe représente la structure de données conforme à recipe.schema.json
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
	} `json:"metadata"`
	IngredientsList []struct {
		ID       string      `json:"id"`
		Name     string      `json:"name"`
		Unit     string      `json:"unit"`
		Amount   interface{} `json:"amount"` // Changé en interface{} pour accepter string et float64
		Category string      `json:"category"`
	} `json:"ingredientsList"`
	SubRecipes []struct {
		ID    string `json:"id"`
		Title string `json:"title"`
		Steps []struct {
			ID     string   `json:"id"`
			Action string   `json:"action"`
			Time   string   `json:"time,omitempty"`
			Tools  []string `json:"tools,omitempty"`
			Inputs []struct {
				Type string `json:"type"`
				Ref  string `json:"ref"`
			} `json:"inputs,omitempty"`
			Output struct {
				State       string `json:"state"`
				Description string `json:"description"`
			} `json:"output,omitempty"`
		} `json:"steps"`
	} `json:"subRecipes"`
}

// RecipeGenerator est responsable de la génération de recettes
type RecipeGenerator struct {
	openAIKey string
}

// NewRecipeGenerator crée une nouvelle instance de RecipeGenerator
func NewRecipeGenerator() *RecipeGenerator {
	openAIKey := os.Getenv("OPENAI_API_KEY")
	if openAIKey == "" {
		log.Error().Msg("OPENAI_API_KEY is not set")
	}
	return &RecipeGenerator{
		openAIKey: openAIKey,
	}
}

// GenerateFromWebContent génère une recette à partir du contenu d'une page web
func (g *RecipeGenerator) GenerateFromWebContent(content string, sourceUrl string, imageUrls []string) (*Recipe, error) {
	if g.openAIKey == "" {
		return nil, fmt.Errorf("OPENAI_API_KEY is not set")
	}

	// Parser l'URL source pour résoudre les URLs relatives
	baseURL, err := url.Parse(sourceUrl)
	if err != nil {
		return nil, fmt.Errorf("invalid source URL: %v", err)
	}

	// Si le contenu n'est pas fourni, le récupérer depuis l'URL
	if content == "" && sourceUrl != "" {
		var err error
		content, err = utils.FetchWebPageContent(sourceUrl)
		if err != nil {
			return nil, fmt.Errorf("failed to fetch web content: %v", err)
		}
	}

	// Extraire le contenu pertinent du HTML
	webContent, err := utils.ExtractWebContent(content)
	if err != nil {
		return nil, fmt.Errorf("failed to extract web content: %v", err)
	}

	// Résoudre les URLs relatives des images
	for i, imgURL := range webContent.ImageURLs {
		if strings.HasPrefix(imgURL, "//") {
			// URL protocol-relative (//example.com/image.jpg)
			webContent.ImageURLs[i] = baseURL.Scheme + ":" + imgURL
		} else if strings.HasPrefix(imgURL, "/") {
			// URL absolute path (/image.jpg)
			webContent.ImageURLs[i] = baseURL.Scheme + "://" + baseURL.Host + imgURL
		} else if !strings.HasPrefix(imgURL, "http") {
			// URL relative (image.jpg ou ../image.jpg)
			ref, err := url.Parse(imgURL)
			if err != nil {
				continue
			}
			webContent.ImageURLs[i] = baseURL.ResolveReference(ref).String()
		}
	}

	// Utiliser les images extraites si aucune n'est fournie
	if len(imageUrls) == 0 && len(webContent.ImageURLs) > 0 {
		imageUrls = webContent.ImageURLs
	}

	// Préparer le prompt pour GPT-4
	systemMessage := fmt.Sprintf(`You are a helpful cooking assistant that transforms webpage content into a structured recipe.

TASK: Convert the following webpage content into a valid recipe JSON following the provided schema.

WEBPAGE TITLE:
%s

WEBPAGE CONTENT:
%s

IMPORTANT RULES:
1. Your response MUST be a valid JSON object matching the Recipe schema
2. Extract recipe details from the webpage content
3. NEVER leave any ingredient without a specific quantity:
   - ALL ingredients MUST have both a unit and an amount
   - Use standard units (g, ml, tsp, tbsp, unit) and precise numbers
   - If a quantity is missing, estimate a reasonable amount
   - For seasonings (salt, pepper), estimate in tsp
   - For liquids "to taste" or "for frying", estimate in ml
   - EVERY ingredient MUST have a category matching its supermarket aisle:
     * "fruits-legumes": Fresh fruits and vegetables
     * "viande": Meat and poultry
     * "poisson": Fish and seafood
     * "cremerie": Dairy, eggs, butter, cream
     * "epicerie-salee": Canned goods, pasta, rice, savory groceries
     * "epicerie-sucree": Sugar, flour, baking needs, sweet groceries
     * "surgele": Frozen foods
     * "condiments": Spices, herbs, seasonings, oils, vinegars
     * "boissons": Drinks and beverages
4. Structure the recipe steps properly:
   - Group related steps into logical subRecipes (e.g., "Sauce", "Main Dish", "Assembly")
   - EVERY step MUST have a time field (e.g., "5min", "1h30min")
   - EVERY step MUST have an inputs array (NEVER null):
     * For steps without ingredients, use an empty array []
     * List ALL ingredients used in the step as "type": "ingredient"
     * Reference previous steps' outputs as "type": "state"
   - EVERY step MUST have a clear output:
     * "state": short description of result (e.g., "mixed", "baked", "chopped")
     * "description": detailed description of the result
   - Chain steps together using state references:
     * If step2 uses the result of step1, include {"type": "state", "ref": "step1"} in step2's inputs
5. Create unique IDs for ingredients and steps
6. Estimate servings, difficulty, and total time based on the content
7. If no clear recipe is found, return an error message

EXAMPLE SCHEMA:
{
  "metadata": {
    "title": "Chocolate Chip Cookies",
    "description": "Classic American cookies with crispy edges and a soft center",
    "servings": 24,
    "difficulty": "easy",
    "totalTime": "45min",
    "image": "chocolate-chip-cookies.jpg",
    "imageUrl": "https://example.com/images/chocolate-chip-cookies.jpg",
    "sourceUrl": "https://example.com/recipes/chocolate-chip-cookies"
  },
  "ingredientsList": [
    {
      "id": "ing1",
      "name": "all-purpose flour",
      "unit": "g",
      "amount": 250,
      "category": "epicerie-sucree"
    }
  ],
  "subRecipes": [
    {
      "id": "sub1",
      "title": "Preparation",
      "steps": [
        {
          "id": "step1",
          "action": "Preheat oven to 375°F (190°C)",
          "time": "10min",
          "tools": ["oven"],
          "inputs": [],
          "output": {
            "state": "preheated",
            "description": "Oven preheated to correct temperature"
          }
        },
        {
          "id": "step2",
          "action": "Mix flour and other dry ingredients",
          "time": "2min",
          "tools": ["bowl", "whisk"],
          "inputs": [
            {
              "type": "ingredient",
              "ref": "ing1"
            }
          ],
          "output": {
            "state": "mixed",
            "description": "Dry ingredients well combined"
          }
        }
      ]
    }
  ]
}`, webContent.Title, webContent.MainContent)

	requestBody := map[string]interface{}{
		"model": "gpt-4-1106-preview",
		"messages": []map[string]string{
			{
				"role":    "system",
				"content": systemMessage,
			},
		},
		"response_format": map[string]interface{}{
			"type": "json_object",
		},
		"temperature": 0.7,
	}

	jsonBody, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("error marshaling request: %v", err)
	}

	// Faire la requête à l'API OpenAI
	req, err := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("error creating request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+g.openAIKey)

	client := &http.Client{Timeout: 300 * time.Second} // 5 minutes
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("error making request: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("error reading response: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("OpenAI API error: %s", string(body))
	}

	var openaiResponse struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	if err := json.Unmarshal(body, &openaiResponse); err != nil {
		return nil, fmt.Errorf("error parsing OpenAI response: %v", err)
	}

	if len(openaiResponse.Choices) == 0 {
		return nil, fmt.Errorf("no response from OpenAI")
	}

	// Parse la recette générée
	var recipe Recipe
	recipeContent := openaiResponse.Choices[0].Message.Content
	log.Info().Str("content", recipeContent).Msg("OpenAI response content")

	// Valider le JSON par rapport au schéma
	schemaLoader := gojsonschema.NewReferenceLoader("file://internal/schema/recipe.schema.json")
	documentLoader := gojsonschema.NewStringLoader(recipeContent)

	result, err := gojsonschema.Validate(schemaLoader, documentLoader)
	if err != nil {
		return nil, fmt.Errorf("error validating recipe schema: %v", err)
	}

	if !result.Valid() {
		var errors []string
		for _, desc := range result.Errors() {
			errors = append(errors, desc.String())
		}
		return nil, fmt.Errorf("recipe does not match schema: %v", errors)
	}

	if err := json.Unmarshal([]byte(recipeContent), &recipe); err != nil {
		log.Error().Err(err).Str("content", recipeContent).Msg("Error unmarshaling recipe")
		return nil, fmt.Errorf("error parsing recipe: %v", err)
	}

	// Ajouter l'URL source et l'image s'ils sont fournis
	recipe.Metadata.SourceUrl = sourceUrl
	if len(imageUrls) > 0 {
		recipe.Metadata.ImageUrl = imageUrls[0]
	}

	return &recipe, nil
}

// ToJSON convertit la recette en JSON
func (r *Recipe) ToJSON() ([]byte, error) {
	// Convertir les amounts en float64 quand c'est possible
	for i, ingredient := range r.IngredientsList {
		switch v := ingredient.Amount.(type) {
		case string:
			if v == "" {
				r.IngredientsList[i].Amount = 0.0
			} else {
				// Si c'est une chaîne non vide, on la garde telle quelle
				r.IngredientsList[i].Amount = v
			}
		case float64:
			// Garder le float64 tel quel
		case int:
			// Convertir les entiers en float64
			r.IngredientsList[i].Amount = float64(v)
		default:
			// Pour tout autre type, mettre 0.0
			r.IngredientsList[i].Amount = 0.0
		}
	}

	return json.MarshalIndent(r, "", "  ")
}
