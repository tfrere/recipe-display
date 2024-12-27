package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"

	"recipe-display/server/internal/models"
)

const serverURL = "http://localhost:3001"

func main() {
	// Test getAllRecipes
	fmt.Println("Testing GET /api/recipes...")
	resp, err := http.Get(serverURL + "/api/recipes")
	if err != nil {
		fmt.Printf("Error making request: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Error reading response: %v\n", err)
		os.Exit(1)
	}

	var recipes []*models.UIRecipe
	if err := json.Unmarshal(body, &recipes); err != nil {
		fmt.Printf("Error parsing response as UIRecipe array: %v\n", err)
		fmt.Println("Response body:", string(body))
		os.Exit(1)
	}

	fmt.Printf("✓ Got %d recipes\n", len(recipes))
	for _, recipe := range recipes {
		fmt.Printf("- %s (%d sub-recipes)\n", recipe.Title, len(recipe.SubRecipes))
	}

	// Test getRecipeBySlug
	slug := "persian-love-rice-with-burnt-butter-tzatziki"
	fmt.Printf("\nTesting GET /api/recipes/%s...\n", slug)
	resp, err = http.Get(serverURL + "/api/recipes/" + slug)
	if err != nil {
		fmt.Printf("Error making request: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	body, err = io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Error reading response: %v\n", err)
		os.Exit(1)
	}

	var recipe models.UIRecipe
	if err := json.Unmarshal(body, &recipe); err != nil {
		fmt.Printf("Error parsing response as UIRecipe: %v\n", err)
		fmt.Println("Response body:", string(body))
		os.Exit(1)
	}

	fmt.Printf("✓ Got recipe: %s\n", recipe.Title)
	fmt.Printf("  - %d ingredients in %d categories\n", len(recipe.Ingredients), len(getCategories(recipe.Ingredients)))
	fmt.Printf("  - %d sub-recipes:\n", len(recipe.SubRecipes))
	for id, sub := range recipe.SubRecipes {
		fmt.Printf("    • %s: %d steps, %d ingredients\n", sub.Title, len(sub.Steps), len(sub.Ingredients))
		for ingID := range sub.Ingredients {
			fmt.Printf("      - %s: %.2f %s\n", recipe.Ingredients[ingID].Name, sub.Ingredients[ingID].Amount, recipe.Ingredients[ingID].Unit)
		}
	}
}

func getCategories(ingredients map[string]struct {
	Name     string `json:"name"`
	Unit     string `json:"unit"`
	Category string `json:"category"`
}) map[string]struct{} {
	categories := make(map[string]struct{})
	for _, ing := range ingredients {
		categories[ing.Category] = struct{}{}
	}
	return categories
}
