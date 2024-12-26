package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
)

type GenerateRecipeRequest struct {
	Source string `json:"source"`
}

type Recipe struct {
	Metadata Metadata `json:"metadata"`
	Data     json.RawMessage `json:"data"`
}

type Metadata struct {
	Title       string `json:"title"`
	Description string `json:"description"`
}

func createSlug(title string) string {
	// This function is not defined in the provided code, so I'm assuming it's defined elsewhere
	// If not, you'll need to implement it
	return title
}

func generateRecipeHandler(w http.ResponseWriter, r *http.Request) {
	log.Println("Generate recipe handler called")
	
	// Logging for debugging
	log.Printf("Request method: %s", r.Method)

	// CORS headers
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	// Handle preflight requests
	if r.Method == "OPTIONS" {
		log.Println("Handling OPTIONS request")
		w.WriteHeader(http.StatusOK)
		return
	}

	if r.Method != "POST" {
		log.Printf("Invalid method: %s", r.Method)
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req GenerateRecipeRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		log.Printf("Error decoding request: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	log.Printf("Received source: %s", req.Source)

	// Create a mock recipe
	mockRecipe := Recipe{
		Metadata: Metadata{
			Title:       "Mock Recipe from " + req.Source,
			Description: "A mock recipe generated for testing",
		},
		Data: json.RawMessage(`{
			"servings": 4,
			"time": {
				"preparation": 15,
				"cooking": 30,
				"total": 45
			},
			"ingredients": [
				{
					"category": "Main",
					"items": [
						{"name": "Test Ingredient", "quantity": 200, "unit": "g"}
					]
				}
			],
			"preparation_steps": [
				{"number": 1, "text": "Test preparation step"}
			]
		}`),
	}

	// Save mock recipe
	filename := fmt.Sprintf("%s.recipe.json", createSlug(mockRecipe.Metadata.Title))
	filepath := filepath.Join("./data", filename)

	jsonData, err := json.MarshalIndent(mockRecipe, "", "  ")
	if err != nil {
		log.Printf("Error marshaling recipe: %v", err)
		http.Error(w, "Failed to generate recipe", http.StatusInternalServerError)
		return
	}

	err = os.WriteFile(filepath, jsonData, 0644)
	if err != nil {
		log.Printf("Error saving recipe: %v", err)
		http.Error(w, "Failed to save recipe", http.StatusInternalServerError)
		return
	}

	log.Println("Recipe generated successfully")
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]string{
		"message": "Recipe generated successfully",
		"slug":    createSlug(mockRecipe.Metadata.Title),
	})
}
