package schema

import (
	"embed"
)

//go:embed recipe.schema.json
var schemaFS embed.FS

// GetRecipeSchema returns the reference JSON schema for recipes
func GetRecipeSchema() (string, error) {
	schemaBytes, err := schemaFS.ReadFile("recipe.schema.json")
	if err != nil {
		return "", err
	}
	return string(schemaBytes), nil
}

// ValidateRecipe validates a recipe against the schema
func ValidateRecipe(recipe map[string]interface{}) error {
	// TODO: Implement JSON Schema validation
	return nil
}
