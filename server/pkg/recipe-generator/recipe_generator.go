package recipegenerator

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/rs/zerolog/log"
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
		ID     string      `json:"id"`
		Name   string      `json:"name"`
		Unit   string      `json:"unit"`
		Amount interface{} `json:"amount"` // Changé en interface{} pour accepter string et float64
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

	// Préparer le prompt pour GPT-4
	systemMessage := fmt.Sprintf(`You are a helpful cooking assistant that transforms webpage content into a structured recipe.

TASK: Convert the following webpage content into a valid recipe JSON following the provided schema.

WEBPAGE CONTENT:
%s

IMPORTANT RULES:
1. Your response MUST be a valid JSON object matching the Recipe schema
2. Extract recipe details from the webpage content
3. If information is missing, use reasonable defaults
4. Ensure all required fields are filled
5. Create unique IDs for ingredients and steps
6. Estimate servings, difficulty, and total time based on the content
7. If no clear recipe is found, return an error message

EXAMPLE SCHEMA:
{
  "metadata": {
    "title": "Recipe Title",
    "description": "Recipe description",
    "servings": 4,
    "difficulty": "medium",
    "totalTime": "45min",
    "image": "recipe-image.jpg",
    "imageUrl": "https://example.com/image.jpg",
    "sourceUrl": "https://example.com/recipe"
  },
  "ingredientsList": [
    {
      "id": "ingredient1",
      "name": "Ingredient Name",
      "unit": "g",
      "amount": 200
    }
  ],
  "subRecipes": [
    {
      "id": "sub1",
      "title": "Main Recipe",
      "steps": [
        {
          "id": "step1",
          "action": "Step description",
          "time": "10min",
          "tools": ["tool1"],
          "inputs": [
            {
              "type": "ingredient",
              "ref": "ingredient1"
            }
          ],
          "output": {
            "state": "final",
            "description": "Result description"
          }
        }
      ]
    }
  ]
}`, content)

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

	client := &http.Client{Timeout: 300 * time.Second}  // 5 minutes
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
	log.Info().Str("content", openaiResponse.Choices[0].Message.Content).Msg("OpenAI response content")
	
	if err := json.Unmarshal([]byte(openaiResponse.Choices[0].Message.Content), &recipe); err != nil {
		log.Error().Err(err).Str("content", openaiResponse.Choices[0].Message.Content).Msg("Error unmarshaling recipe")
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
