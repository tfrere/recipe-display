package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/disintegration/imaging"
	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
	"github.com/kolesa-team/go-webp/encoder"
	"github.com/kolesa-team/go-webp/webp"
)

type Metadata struct {
	Title       string `json:"title"`
	Description string `json:"description"`
}

type Recipe struct {
	Metadata Metadata        `json:"metadata"`
	Data     json.RawMessage `json:"data,omitempty"`
}

func createSlug(input string) string {
	// Convert to lowercase
	slug := strings.ToLower(input)
	
	// Replace accented characters
	replacements := map[string]string{
		"é": "e", "è": "e", "ê": "e", "ë": "e",
		"à": "a", "â": "a", "ä": "a",
		"î": "i", "ï": "i",
		"ô": "o", "ö": "o",
		"ù": "u", "û": "u", "ü": "u",
		"ÿ": "y",
		"ç": "c",
	}
	
	for accent, normal := range replacements {
		slug = strings.ReplaceAll(slug, accent, normal)
	}
	
	// Replace spaces and special characters with hyphens
	reg := regexp.MustCompile("[^a-z0-9]+")
	slug = reg.ReplaceAllString(slug, "-")
	
	// Remove leading and trailing hyphens
	slug = strings.Trim(slug, "-")
	
	return slug
}

func getAllRecipes(w http.ResponseWriter, r *http.Request) {
	recipesDir := "./data"
	files, err := os.ReadDir(recipesDir)
	if err != nil {
		http.Error(w, "Failed to read recipes directory", http.StatusInternalServerError)
		return
	}

	var recipes []map[string]interface{}
	for _, file := range files {
		if !file.IsDir() && strings.HasSuffix(file.Name(), ".recipe.json") && file.Name() != "recipe.schema.json" {
			data, err := os.ReadFile(filepath.Join(recipesDir, file.Name()))
			if err != nil {
				continue
			}

			var recipe struct {
				Metadata struct {
					Title       string `json:"title"`
					Description string `json:"description"`
					Image       string `json:"image"`
				} `json:"metadata"`
			}
			if err := json.Unmarshal(data, &recipe); err != nil {
				continue
			}

			slug := createSlug(recipe.Metadata.Title)
			recipes = append(recipes, map[string]interface{}{
				"title":       recipe.Metadata.Title,
				"description": recipe.Metadata.Description,
				"image":       recipe.Metadata.Image,
				"slug":        slug,
			})
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(recipes)
}

func findRecipeBySlug(slug string) (string, error) {
	recipesDir := "./data"
	files, err := os.ReadDir(recipesDir)
	if err != nil {
		return "", err
	}

	for _, file := range files {
		if !file.IsDir() && strings.HasSuffix(file.Name(), ".recipe.json") && file.Name() != "recipe.schema.json" {
			data, err := os.ReadFile(filepath.Join(recipesDir, file.Name()))
			if err != nil {
				continue
			}

			var recipe Recipe
			if err := json.Unmarshal(data, &recipe); err != nil {
				continue
			}

			if createSlug(recipe.Metadata.Title) == slug {
				return string(data), nil
			}
		}
	}
	return "", os.ErrNotExist
}

func getRecipeBySlug(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	slug := vars["slug"]
	
	log.Printf("Looking for recipe with slug: %s", slug)

	recipeData, err := findRecipeBySlug(slug)
	if err != nil {
		log.Printf("Recipe not found for slug: %s. Error: %v", slug, err)
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	// Log the raw recipe data for debugging
	log.Printf("Found recipe data for slug %s: %s", slug, recipeData)

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(recipeData))
}

// ImageSize représente les tailles d'images disponibles
type ImageSize struct {
	Name   string
	Width  int
	Height int
}

var (
	imageSizes = []ImageSize{
		{Name: "thumbnail", Width: 200, Height: 200},
		{Name: "small", Width: 400, Height: 400},
		{Name: "medium", Width: 800, Height: 800},
		{Name: "large", Width: 1200, Height: 1200},
	}
	imageCache = sync.Map{}
)

// setupImageDirectories crée les dossiers nécessaires pour les images
func setupImageDirectories() error {
	baseDir := "./data/images"
	dirs := []string{"original", "large", "medium", "small", "thumbnail"}
	
	for _, dir := range dirs {
		path := filepath.Join(baseDir, dir)
		if err := os.MkdirAll(path, 0755); err != nil {
			return fmt.Errorf("failed to create directory %s: %v", path, err)
		}
	}
	return nil
}

// getResizedImagePath retourne le chemin de l'image redimensionnée
func getResizedImagePath(originalPath, size string) string {
	baseDir := filepath.Dir(filepath.Dir(originalPath)) // Remonte d'un niveau pour sortir du dossier 'original'
	filename := filepath.Base(originalPath)
	// Convertir toutes les images en WebP pour une meilleure compression
	filenameWithoutExt := strings.TrimSuffix(filename, filepath.Ext(filename))
	return filepath.Join(baseDir, size, filenameWithoutExt + ".webp")
}

// isValidImageFormat vérifie si le format de l'image est supporté
func isValidImageFormat(filename string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	validExtensions := map[string]bool{
		".jpg":  true,
		".jpeg": true,
		".png":  true,
		".webp": true,
		".gif":  true,
	}
	return validExtensions[ext]
}

// resizeImage redimensionne l'image si nécessaire
func resizeImage(originalPath string, size ImageSize) (string, error) {
	// Vérifier si l'image redimensionnée existe déjà dans le cache
	cacheKey := fmt.Sprintf("%s-%s", originalPath, size.Name)
	if cachedPath, ok := imageCache.Load(cacheKey); ok {
		return cachedPath.(string), nil
	}

	// Créer le chemin pour l'image redimensionnée
	resizedPath := getResizedImagePath(originalPath, size.Name)

	// Vérifier si l'image redimensionnée existe déjà sur le disque
	if _, err := os.Stat(resizedPath); err == nil {
		imageCache.Store(cacheKey, resizedPath)
		return resizedPath, nil
	}

	// Ouvrir l'image originale
	src, err := imaging.Open(originalPath)
	if err != nil {
		return "", fmt.Errorf("failed to open image: %v", err)
	}

	// Redimensionner l'image
	resized := imaging.Fit(src, size.Width, size.Height, imaging.Lanczos)

	// Créer le dossier de destination s'il n'existe pas
	if err := os.MkdirAll(filepath.Dir(resizedPath), 0755); err != nil {
		return "", fmt.Errorf("failed to create directory: %v", err)
	}

	// Encoder l'image en WebP
	output, err := os.Create(resizedPath)
	if err != nil {
		return "", fmt.Errorf("failed to create output file: %v", err)
	}
	defer output.Close()

	options, err := encoder.NewLossyEncoderOptions(encoder.PresetDefault, 75)
	if err != nil {
		return "", fmt.Errorf("failed to create encoder options: %v", err)
	}

	if err := webp.Encode(output, resized, options); err != nil {
		return "", fmt.Errorf("failed to encode WebP: %v", err)
	}

	// Mettre en cache le chemin
	imageCache.Store(cacheKey, resizedPath)

	return resizedPath, nil
}

func serveImage(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	size := vars["size"]
	filename := vars["filename"]

	// Validate size
	validSizes := map[string]bool{
		"small":     true,
		"medium":    true,
		"large":     true,
		"thumbnail": true,
	}
	if !validSizes[size] {
		http.Error(w, "Invalid image size", http.StatusBadRequest)
		return
	}

	// Construct original image path
	originalPath := filepath.Join("./data/images/original", filename)

	// If image doesn't exist, try different extensions
	if _, err := os.Stat(originalPath); os.IsNotExist(err) {
		for _, ext := range []string{".jpg", ".jpeg", ".png", ".webp", ".gif"} {
			baseFilename := strings.TrimSuffix(filename, filepath.Ext(filename))
			testPath := filepath.Join("./data/images/original", baseFilename+ext)
			if _, err := os.Stat(testPath); err == nil {
				originalPath = testPath
				break
			}
		}
	}

	// Resize image to requested size
	resizedPath, err := resizeImage(originalPath, ImageSize{Name: size, Width: 800, Height: 800})
	if err != nil {
		log.Printf("Error resizing image: %v", err)
		http.Error(w, "Error processing image", http.StatusInternalServerError)
		return
	}

	// Serve the image
	http.ServeFile(w, r, resizedPath)
}

func fetchWebPageContent(urlStr string) (string, error) {
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

func callOpenAIRecipeGeneration(htmlContent, sourceURL string) (map[string]interface{}, error) {
	// Prepare the API request to OpenAI
	openaiAPIKey := os.Getenv("OPENAI_API_KEY")
	if openaiAPIKey == "" {
		return nil, fmt.Errorf("OpenAI API key not set")
	}

	// Construct the prompt with clear instructions
	prompt := fmt.Sprintf(`
	Parse the following HTML and generate a structured recipe JSON that exactly matches this schema:
	- Must have a 'metadata' section with title, description, servings, difficulty, totalTime, and image
	- 'ingredients' should be a map with detailed ingredient objects
	- Include a 'subRecipes' section if applicable
	- Provide full 'instructions' list
	- Add source URL in 'data' section

	Source URL: %s
	HTML Content:
	%s
	`, sourceURL, htmlContent)

	// Prepare the request body
	requestBody := map[string]interface{}{
		"model": "gpt-4o",
		"messages": []map[string]string{
			{
				"role":    "system",
				"content": "You are a recipe parsing assistant. Return a JSON that exactly matches the specified schema.",
			},
			{
				"role":    "user",
				"content": prompt,
			},
		},
		"response_format": map[string]string{
			"type": "json_object",
		},
	}

	jsonBody, _ := json.Marshal(requestBody)

	// Create HTTP request to OpenAI
	req, err := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("error creating OpenAI request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+openaiAPIKey)

	// Send request
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("error sending request to OpenAI: %v", err)
	}
	defer resp.Body.Close()

	// Read response
	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("error reading OpenAI response: %v", err)
	}

	// Parse the response
	var openaiResponse map[string]interface{}
	if err := json.Unmarshal(responseBody, &openaiResponse); err != nil {
		return nil, fmt.Errorf("error parsing OpenAI response: %v", err)
	}

	// Extract the generated recipe
	choices, ok := openaiResponse["choices"].([]interface{})
	if !ok || len(choices) == 0 {
		return nil, fmt.Errorf("no recipe generated")
	}

	choice := choices[0].(map[string]interface{})
	message := choice["message"].(map[string]interface{})
	
	// Parse the recipe JSON
	var recipe map[string]interface{}
	if err := json.Unmarshal([]byte(message["content"].(string)), &recipe); err != nil {
		return nil, fmt.Errorf("error parsing recipe JSON: %v", err)
	}

	return recipe, nil
}

func generateRecipeHandler(w http.ResponseWriter, r *http.Request) {
	// Start timing the request
	startTime := time.Now()

	// Parse the incoming JSON request
	var requestBody struct {
		Source string `json:"source"`
	}

	// Read request body
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		log.Printf(" [Recipe Generation] Error reading request body: %v", err)
		http.Error(w, "Error reading request body", http.StatusBadRequest)
		return
	}

	// Decode the request body
	if err := json.Unmarshal(body, &requestBody); err != nil {
		log.Printf(" [Recipe Generation] Error parsing request body: %v", err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate source URL
	if requestBody.Source == "" {
		log.Printf(" [Recipe Generation] Empty source URL")
		http.Error(w, "Source URL is required", http.StatusBadRequest)
		return
	}

	// Fetch web page content
	htmlContent, err := fetchWebPageContent(requestBody.Source)
	if err != nil {
		log.Printf(" [Recipe Generation] Error fetching web page: %v", err)
		http.Error(w, "Error fetching recipe webpage", http.StatusInternalServerError)
		return
	}

	// Generate recipe using OpenAI
	recipe, err := callOpenAIRecipeGeneration(htmlContent, requestBody.Source)
	if err != nil {
		log.Printf(" [Recipe Generation] Error generating recipe: %v", err)
		http.Error(w, "Error generating recipe", http.StatusInternalServerError)
		return
	}

	// Generate a slug for the recipe
	var slug string
	if title, ok := recipe["metadata"].(map[string]interface{})["title"].(string); ok && title != "" {
		slug = createSlug(title)
	} else {
		// Fallback to creating slug from source URL if title is not available
		slug = createSlug(requestBody.Source)
	}
	log.Printf(" [Recipe Generation] Generated slug: %s", slug)

	// Prepare file path for saving
	recipeFilePath := filepath.Join("./data", slug+".recipe.json")

	// Encode the recipe to JSON
	jsonData, err := json.MarshalIndent(recipe, "", "  ")
	if err != nil {
		log.Printf(" [Recipe Generation] Error marshaling recipe: %v", err)
		http.Error(w, "Error generating recipe", http.StatusInternalServerError)
		return
	}

	// Save the recipe to a file
	err = ioutil.WriteFile(recipeFilePath, jsonData, 0644)
	if err != nil {
		log.Printf(" [Recipe Generation] Error saving recipe file: %v", err)
		http.Error(w, "Error saving recipe", http.StatusInternalServerError)
		return
	}

	// Log successful generation
	duration := time.Since(startTime)
	log.Printf(" [Recipe Generation] Successfully generated recipe from %s in %v", requestBody.Source, duration)

	// Send the recipe back to the client
	w.Header().Set("Content-Type", "application/json")
	w.Write(jsonData)
}

func main() {
	// Setup logging
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	
	// Load environment variables
	err := godotenv.Load()
	if err != nil {
		log.Println("Error loading .env file, using system environment")
	}

	// Setup image directories
	if err := setupImageDirectories(); err != nil {
		log.Fatalf("Failed to setup image directories: %v", err)
	}

	// Create router
	r := mux.NewRouter()

	// Add middleware
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			log.Printf("REQUEST: %s %s", r.Method, r.URL.Path)
			next.ServeHTTP(w, r)
		})
	})

	// CORS middleware
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			
			if r.Method == "OPTIONS" {
				w.WriteHeader(http.StatusOK)
				return
			}
			
			next.ServeHTTP(w, r)
		})
	})

	// Recipe routes
	r.HandleFunc("/api/recipes", getAllRecipes).Methods("GET")
	r.HandleFunc("/api/recipes/{slug}", getRecipeBySlug).Methods("GET")
	r.HandleFunc("/api/recipes/generate", generateRecipeHandler).Methods("POST", "OPTIONS")

	// Image routes
	r.HandleFunc("/api/images/{size}/{filename}", serveImage).Methods("GET")

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "3001"
	}

	log.Printf(" Server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}
