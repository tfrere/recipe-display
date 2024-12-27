package utils

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/rs/zerolog/log"
	"recipe-display/server/internal/models"
	"golang.org/x/net/html"
)

func FetchWebPageContent(urlStr string) (string, error) {
	// Create a new HTTP client
	client := &http.Client{
		Timeout: 10 * time.Second,
	}

	// Create the request
	req, err := http.NewRequest("GET", urlStr, nil)
	if err != nil {
		return "", fmt.Errorf("error creating request: %v", err)
	}

	// Set a user agent to mimic a browser
	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36")

	// Send the request
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("error fetching URL: %v", err)
	}
	defer resp.Body.Close()

	// Check response status
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("bad status code: %d", resp.StatusCode)
	}

	// Read the body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("error reading response body: %v", err)
	}

	return string(body), nil
}

func ExtractRecipeInfo(htmlContent string) (string, string, error) {
	doc, err := html.Parse(strings.NewReader(htmlContent))
	if err != nil {
		return "", "", fmt.Errorf("error parsing HTML: %v", err)
	}

	var imageUrl, sourceUrl string

	// Fonction récursive pour parcourir le DOM
	var findUrls func(*html.Node)
	findUrls = func(n *html.Node) {
		if n.Type == html.ElementNode {
			// Chercher l'image principale
			if n.Data == "meta" {
				var property, content string
				for _, a := range n.Attr {
					if a.Key == "property" && (a.Val == "og:image" || a.Val == "twitter:image") {
						property = a.Val
					}
					if a.Key == "content" {
						content = a.Val
					}
				}
				if property != "" && content != "" && imageUrl == "" {
					imageUrl = content
				}
			}

			// Chercher l'URL canonique
			if n.Data == "link" {
				var rel, href string
				for _, a := range n.Attr {
					if a.Key == "rel" && a.Val == "canonical" {
						rel = a.Val
					}
					if a.Key == "href" {
						href = a.Val
					}
				}
				if rel == "canonical" && href != "" {
					sourceUrl = href
				}
			}
		}

		for c := n.FirstChild; c != nil; c = c.NextSibling {
			findUrls(c)
		}
	}

	findUrls(doc)

	return imageUrl, sourceUrl, nil
}

func ExtractWebpageContent(htmlContent string) string {
	doc, err := html.Parse(strings.NewReader(htmlContent))
	if err != nil {
		log.Error().Err(err).Msg("Error parsing HTML")
		return ""
	}

	var extractText func(*html.Node) string
	extractText = func(n *html.Node) string {
		// Récupérer TOUT le texte, sans exception
		if n.Type == html.TextNode {
			return strings.TrimSpace(n.Data)
		}

		var text string
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			text += extractText(c) + " "
		}

		return text
	}

	var extractLinks func(*html.Node) []string
	extractLinks = func(n *html.Node) []string {
		var links []string
		if n.Type == html.ElementNode && n.Data == "a" {
			for _, a := range n.Attr {
				if a.Key == "href" && (strings.HasPrefix(a.Val, "http://") || strings.HasPrefix(a.Val, "https://")) {
					links = append(links, a.Val)
				}
			}
		}

		for c := n.FirstChild; c != nil; c = c.NextSibling {
			links = append(links, extractLinks(c)...)
		}

		return links
	}

	text := extractText(doc)
	links := extractLinks(doc)

	// Combiner le texte et les liens
	result := fmt.Sprintf("Webpage Content:\n%s\n\nLinks:\n%s", 
		text, 
		strings.Join(links, "\n"))

	return result
}

func GenerateRecipe(prompt string) (*models.UIRecipe, error) {
	openAIKey := os.Getenv("OPENAI_API_KEY")
	if openAIKey == "" {
		return nil, fmt.Errorf("OPENAI_API_KEY is not set")
	}

	// Variables pour les URLs
	var extractedContent string

	// Extraire l'URL du prompt si elle existe
	if strings.Contains(prompt, "http://") || strings.Contains(prompt, "https://") {
		// Trouver l'URL dans le prompt
		words := strings.Fields(prompt)
		var url string
		for _, word := range words {
			if strings.HasPrefix(word, "http://") || strings.HasPrefix(word, "https://") {
				url = word
				break
			}
		}

		// Récupérer le contenu de la page et extraire les informations
		if url != "" {
			content, err := FetchWebPageContent(url)
			if err != nil {
				log.Error().Err(err).Msg("Failed to fetch webpage content")
			} else {
				// Extraire le contenu textuel et les liens
				extractedContent = ExtractWebpageContent(content)
			}
		}
	}

	// Charger le schéma JSON
	schemaBytes, err := os.ReadFile("internal/schema/recipe.schema.json")
	if err != nil {
		return nil, fmt.Errorf("error reading schema: %v", err)
	}

	var schema map[string]interface{}
	if err := json.Unmarshal(schemaBytes, &schema); err != nil {
		return nil, fmt.Errorf("error parsing schema: %v", err)
	}

	// Préparer la requête OpenAI
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
    "image": "recipe-image.jpg"
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
}

Your task is to transform the webpage content into this structured format.`, extractedContent)

	requestBody := map[string]interface{}{
		"model": "gpt-4-1106-preview",
		"messages": []map[string]string{
			{
				"role":    "system",
				"content": systemMessage,
			},
			{
				"role":    "user",
				"content": prompt,
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
	req.Header.Set("Authorization", "Bearer "+openAIKey)

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
	var recipe models.Recipe
	log.Info().Str("content", openaiResponse.Choices[0].Message.Content).Msg("OpenAI response content")
	
	if err := json.Unmarshal([]byte(openaiResponse.Choices[0].Message.Content), &recipe); err != nil {
		log.Error().Err(err).Str("content", openaiResponse.Choices[0].Message.Content).Msg("Error unmarshaling recipe")
		return nil, fmt.Errorf("error parsing recipe: %v", err)
	}

	// Vérifier que les champs requis sont présents
	if recipe.Metadata.Title == "" {
		log.Error().Interface("metadata", recipe.Metadata).Msg("Recipe metadata is missing title")
		return nil, fmt.Errorf("generated recipe is missing title")
	}

	// Convertir en format UI
	uiRecipe := recipe.ConvertToUIRecipe()
	return uiRecipe, nil
}
