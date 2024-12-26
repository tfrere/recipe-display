package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"

	"github.com/disintegration/imaging"
	"github.com/gorilla/mux"
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

// Middleware for logging requests
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("Request: %s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
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
		log.Printf("Recipe not found for slug: %s", slug)
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

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

// serveImage gère les requêtes d'images
func serveImage(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	imageName := vars["image"]
	size := vars["size"]

	// Vérifier si la taille demandée est valide
	var targetSize ImageSize
	validSize := false
	for _, s := range imageSizes {
		if s.Name == size {
			targetSize = s
			validSize = true
			break
		}
	}

	if !validSize {
		http.Error(w, "Invalid size parameter", http.StatusBadRequest)
		return
	}

	// Construire le chemin de l'image originale
	originalPath := filepath.Join("./data/images/original", imageName)

	// Si l'image n'existe pas directement, chercher avec différentes extensions
	if _, err := os.Stat(originalPath); os.IsNotExist(err) {
		found := false
		baseFilename := strings.TrimSuffix(imageName, filepath.Ext(imageName))
		validExtensions := []string{".jpg", ".jpeg", ".png", ".webp", ".gif"}
		
		for _, ext := range validExtensions {
			testPath := filepath.Join("./data/images/original", baseFilename + ext)
			if _, err := os.Stat(testPath); err == nil {
				originalPath = testPath
				found = true
				break
			}
		}

		if !found {
			http.Error(w, "Image not found", http.StatusNotFound)
			return
		}
	}

	// Vérifier si le format est valide
	if !isValidImageFormat(originalPath) {
		http.Error(w, "Invalid image format", http.StatusBadRequest)
		return
	}

	// Redimensionner l'image si nécessaire
	resizedPath, err := resizeImage(originalPath, targetSize)
	if err != nil {
		log.Printf("Error resizing image: %v", err)
		http.Error(w, "Error processing image", http.StatusInternalServerError)
		return
	}

	// Définir les en-têtes de cache et de type MIME
	w.Header().Set("Cache-Control", "public, max-age=31536000")
	w.Header().Set("Content-Type", "image/webp")
	http.ServeFile(w, r, resizedPath)
}

func main() {
	// Initialiser les dossiers d'images
	if err := setupImageDirectories(); err != nil {
		log.Fatal(err)
	}

	r := mux.NewRouter()

	// Add logging middleware
	r.Use(loggingMiddleware)

	// Enable CORS
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			if r.Method == "OPTIONS" {
				w.WriteHeader(http.StatusOK)
				return
			}
			next.ServeHTTP(w, r)
		})
	})

	// API routes
	api := r.PathPrefix("/api").Subrouter()
	api.HandleFunc("/recipes", getAllRecipes).Methods("GET", "OPTIONS")
	api.HandleFunc("/recipe/{slug}", getRecipeBySlug).Methods("GET", "OPTIONS")
	
	// Route pour les images
	api.HandleFunc("/images/{size}/{image}", serveImage).Methods("GET")

	log.Println("Server starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", r))
}
