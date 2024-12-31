package recipegenerator

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"text/template"
	"time"

	"recipe-display/server/internal/utils"

	"github.com/rs/zerolog/log"
	"github.com/xeipuuv/gojsonschema"
)

// RecipeGenerator est responsable de la génération de recettes
type RecipeGenerator struct {
	openAIKey string
	constants *Constants
}

// NewRecipeGenerator crée une nouvelle instance de RecipeGenerator
func NewRecipeGenerator() *RecipeGenerator {
	openAIKey := os.Getenv("OPENAI_API_KEY")
	if openAIKey == "" {
		log.Error().Msg("OPENAI_API_KEY is not set")
	}

	// Charger les constantes
	constants, err := loadConstants()
	if err != nil {
		log.Error().Err(err).Msg("Failed to load constants")
	}

	return &RecipeGenerator{
		openAIKey: openAIKey,
		constants: constants,
	}
}

// GenerateFromWebContent génère une recette à partir du contenu d'une page web
func (rg *RecipeGenerator) GenerateFromWebContent(webContent *utils.WebContent, sourceUrl string, imageUrls []string) (*Recipe, error) {
	if webContent == nil {
		return nil, fmt.Errorf("web content is nil")
	}

	if rg.openAIKey == "" {
		return nil, fmt.Errorf("OPENAI_API_KEY is not set")
	}

	// Première étape : nettoyer et organiser le contenu de la recette
	cleanedContent, err := rg.cleanupRecipeContent(webContent)
	if err != nil {
		return nil, fmt.Errorf("failed to cleanup recipe content: %w", err)
	}

	// Deuxième étape : générer la recette structurée
	recipe, err := rg.generateStructuredRecipe(cleanedContent, sourceUrl, imageUrls)
	if err != nil {
		return nil, fmt.Errorf("failed to generate structured recipe: %w", err)
	}

	return recipe, nil
}

// cleanupRecipeContent nettoie et organise le contenu de la recette
func (rg *RecipeGenerator) cleanupRecipeContent(webContent *utils.WebContent) (*utils.WebContent, error) {
	// Préparer le prompt pour le nettoyage
	cleanupMessage := fmt.Sprintf(CleanupPrompt, webContent.Title, webContent.MainContent)

	// Préparer la requête pour l'API d'OpenAI
	requestBody := map[string]interface{}{
		"model": "gpt-4-1106-preview",
		"messages": []map[string]string{
			{
				"role":    "system",
				"content": cleanupMessage,
			},
		},
		"temperature": 0.3, // Température plus basse pour être plus conservateur
		"max_tokens":  4000,
	}

	jsonBody, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request body: %w", err)
	}

	// Créer la requête HTTP
	req, err := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+rg.openAIKey)

	// Envoyer la requête
	client := &http.Client{Timeout: 600 * time.Second} // 10 minutes
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	// Lire la réponse
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	// Décoder la réponse
	var response struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	if err := json.Unmarshal(body, &response); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if len(response.Choices) == 0 {
		return nil, fmt.Errorf("no response choices available")
	}

	// Créer un nouveau WebContent avec le contenu nettoyé
	cleanedContent := &utils.WebContent{
		Title:       webContent.Title,
		MainContent: response.Choices[0].Message.Content,
		ImageURLs:   webContent.ImageURLs,
	}

	log.Info().
		Str("title", cleanedContent.Title).
		Str("cleaned_content", cleanedContent.MainContent).
		Msg("Recipe content after cleanup")

	return cleanedContent, nil
}

// generateStructuredRecipe génère une recette structurée à partir du contenu nettoyé
func (rg *RecipeGenerator) generateStructuredRecipe(webContent *utils.WebContent, sourceUrl string, imageUrls []string) (*Recipe, error) {
	// Préparer le prompt pour GPT-4
	tmpl, err := template.New("prompt").Parse(SystemPrompt)
	if err != nil {
		return nil, fmt.Errorf("error parsing template: %v", err)
	}

	// Exécuter le template avec les constantes
	var buf bytes.Buffer
	err = tmpl.Execute(&buf, rg.constants.formatForTemplate())
	if err != nil {
		return nil, fmt.Errorf("error executing template: %v", err)
	}

	systemMessage := fmt.Sprintf(buf.String(), webContent.Title, webContent.MainContent)

	// Préparer la requête pour l'API d'OpenAI
	requestBody := map[string]interface{}{
		"model": "gpt-4-1106-preview",
		"messages": []map[string]string{
			{
				"role":    "system",
				"content": systemMessage,
			},
		},
		"response_format": map[string]string{
			"type": "json_object",
		},
		"temperature": 0.7,
		"max_tokens":  4000,
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
	req.Header.Set("Authorization", "Bearer "+rg.openAIKey)

	client := &http.Client{Timeout: 600 * time.Second} // 10 minutes
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
		log.Error().
			Err(err).
			Str("schema_path", "internal/schema/recipe.schema.json").
			Str("content", recipeContent).
			Msg("Error validating recipe schema")
		return nil, fmt.Errorf("error validating recipe schema: %v", err)
	}

	if !result.Valid() {
		var errors []string
		for _, desc := range result.Errors() {
			errors = append(errors, desc.String())
			log.Error().
				Str("error", desc.String()).
				Str("field", desc.Field()).
				Str("value", fmt.Sprintf("%v", desc.Value())).
				Msg("Schema validation error")
		}
		return nil, fmt.Errorf("recipe does not match schema: %v", errors)
	}

	if err := json.Unmarshal([]byte(recipeContent), &recipe); err != nil {
		log.Error().Err(err).Str("content", recipeContent).Msg("Error unmarshaling recipe")
		return nil, fmt.Errorf("error parsing recipe: %v", err)
	}

	// Valider les états des ingrédients dans les sous-recettes
	for i := range recipe.SubRecipes {
		// Initialiser la map si elle n'existe pas
		if recipe.SubRecipes[i].Ingredients == nil {
			recipe.SubRecipes[i].Ingredients = make(map[string]SubIngredient)
		}

		// Collecter tous les ingrédients utilisés dans les étapes
		usedIngredients := make(map[string]bool)
		for _, step := range recipe.SubRecipes[i].Steps {
			for _, input := range step.Inputs {
				if input.Type == "ingredient" {
					usedIngredients[input.Ref] = true
				}
			}
		}

		// Vérifier que chaque ingrédient utilisé a une entrée dans la map
		for ingredientID := range usedIngredients {
			_, exists := recipe.SubRecipes[i].Ingredients[ingredientID]
			if !exists {
				// Si l'ingrédient n'est pas dans la map, l'ajouter avec un état vide
				// Trouver l'ingrédient dans la liste globale pour obtenir sa quantité
				var amount interface{}
				for _, ing := range recipe.IngredientsList {
					if ing.ID == ingredientID {
						amount = ing.Amount
						break
					}
				}
				recipe.SubRecipes[i].Ingredients[ingredientID] = SubIngredient{
					Amount: amount,
					State:  "", // État vide par défaut
				}
			}
		}

		// Vérifier qu'il n'y a pas d'ingrédients inutilisés dans la map
		for ingredientID := range recipe.SubRecipes[i].Ingredients {
			if !usedIngredients[ingredientID] {
				log.Warn().
					Str("sub_recipe", recipe.SubRecipes[i].ID).
					Str("ingredient", ingredientID).
					Msg("Ingredient defined in sub-recipe ingredients map but not used in any step")
			}
		}
	}

	// Calculer le temps total de la recette
	totalMinutes := 0
	for _, subRecipe := range recipe.SubRecipes {
		for _, step := range subRecipe.Steps {
			// Parse le temps de l'étape
			if step.Time != "" {
				// Parse hours if present
				if hourMatch := regexp.MustCompile(`(\d+)h`).FindStringSubmatch(step.Time); len(hourMatch) > 1 {
					hours, _ := strconv.Atoi(hourMatch[1])
					totalMinutes += hours * 60
				}
				// Parse minutes if present
				if minMatch := regexp.MustCompile(`(\d+)min`).FindStringSubmatch(step.Time); len(minMatch) > 1 {
					minutes, _ := strconv.Atoi(minMatch[1])
					totalMinutes += minutes
				}
			}
		}
	}

	// Définir si la recette est rapide (moins de 30 minutes)
	recipe.Metadata.Quick = totalMinutes <= 30

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
	for i := range r.IngredientsList {
		// Convert amount to float64
		switch v := r.IngredientsList[i].Amount.(type) {
		case float64:
			r.IngredientsList[i].Amount = v
		case string:
			floatVal, err := strconv.ParseFloat(v, 64)
			if err != nil {
				return nil, fmt.Errorf("error converting amount to float64: %v", err)
			}
			r.IngredientsList[i].Amount = floatVal
		default:
			return nil, fmt.Errorf("unexpected type for amount: %T", v)
		}
	}

	return json.MarshalIndent(r, "", "  ")
}
