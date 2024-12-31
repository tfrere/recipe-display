package recipegenerator

// Recipe représente une recette complète avec ses métadonnées et ses étapes
type Recipe struct {
	Metadata        RecipeMetadata `json:"metadata"`
	IngredientsList []Ingredient   `json:"ingredientsList"`
	SubRecipes      []SubRecipe    `json:"subRecipes"`
}

// RecipeMetadata contient les métadonnées d'une recette
type RecipeMetadata struct {
	Title       string `json:"title"`
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
	Notes       string `json:"notes"`
}

// Ingredient représente un ingrédient dans la recette
type Ingredient struct {
	ID       string      `json:"id"`
	Name     string      `json:"name"`
	Unit     string      `json:"unit"`
	Amount   interface{} `json:"amount"`
	Category string      `json:"category"`
	State    string      `json:"state,omitempty"`
}

// SubRecipe représente une sous-recette avec ses étapes
type SubRecipe struct {
	ID          string                    `json:"id"`
	Title       string                    `json:"title"`
	Ingredients map[string]SubIngredient  `json:"ingredients"`
	Steps       []Step                    `json:"steps"`
}

// SubIngredient représente un ingrédient dans une sous-recette
type SubIngredient struct {
	Amount interface{} `json:"amount"`
	State  string     `json:"state"`
}

// Step représente une étape dans une sous-recette
type Step struct {
	ID      string        `json:"id"`
	Action  string        `json:"action"`
	Time    string        `json:"time"`
	Tools   []string      `json:"tools"`
	Inputs  []StepInput   `json:"inputs"`
	Output  StepOutput    `json:"output"`
}

// StepInput représente une entrée pour une étape
type StepInput struct {
	Type string `json:"type"`
	Ref  string `json:"ref"`
}

// StepOutput représente la sortie d'une étape
type StepOutput struct {
	State       string `json:"state"`
	Description string `json:"description"`
}
