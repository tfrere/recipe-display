package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
	"github.com/rs/cors"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"recipe-display/server/internal/models"
	"recipe-display/server/internal/services"
)

var (
	// Tailles d'images disponibles
	imageSizes = []services.ImageSize{
		{Name: "thumbnail", Width: 200, Height: 200},
		{Name: "small", Width: 400, Height: 400},
		{Name: "medium", Width: 800, Height: 800},
		{Name: "large", Width: 1200, Height: 1200},
		{Name: "original", Width: 0, Height: 0},
	}

	// Configuration des chemins
	dataDir     = "data"
	imagesDir   = filepath.Join(dataDir, "images")
	originalDir = filepath.Join(imagesDir, "original")
)

func init() {
	// Configure zerolog
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	zerolog.SetGlobalLevel(zerolog.DebugLevel)

	// Créer les dossiers nécessaires
	for _, dir := range []string{dataDir, imagesDir, originalDir} {
		if err := os.MkdirAll(dir, 0755); err != nil {
			log.Fatal().Err(err).Str("dir", dir).Msg("Failed to create directory")
		}
	}
}

func serveImage(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	size := vars["size"]
	filename := vars["filename"]
	
	imageService := services.NewImageService(imagesDir)

	// Essayer toutes les extensions possibles
	baseFilename := strings.TrimSuffix(filename, filepath.Ext(filename))
	extensions := []string{".jpg", ".jpeg", ".png", ".gif", ".webp"}
	
	var originalPath string
	var originalFound bool
	
	for _, ext := range extensions {
		testPath := filepath.Join(originalDir, baseFilename+ext)
		if _, err := os.Stat(testPath); err == nil {
			originalPath = testPath
			originalFound = true
			break
		}
	}

	if !originalFound {
		log.Error().Str("filename", filename).Msg("Image not found")
		http.Error(w, "Image not found", http.StatusNotFound)
		return
	}

	resizedPath := originalPath

	// Si une taille est spécifiée, redimensionner l'image
	if size != "" {
		var err error
		resizedPath, err = imageService.GetResizedImagePath(originalPath, size)
		if err != nil {
			log.Error().Err(err).Str("filename", filename).Str("size", size).Msg("Failed to get resized image")
			http.Error(w, "Failed to get resized image", http.StatusInternalServerError)
			return
		}
	}

	// Définir le type MIME pour WebP
	w.Header().Set("Content-Type", "image/webp")
	http.ServeFile(w, r, resizedPath)
}

type RecipeResponse struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Servings    int    `json:"servings"`
	Difficulty  string `json:"difficulty"`
	TotalTime   string `json:"totalTime"`
	Image       string `json:"image"`
	Slug        string `json:"slug"`
	Metadata    struct {
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
	} `json:"metadata"`
	Ingredients map[string]struct {
		Name     string `json:"name"`
		Unit     string `json:"unit"`
		Category string `json:"category"`
		State    string `json:"state"`
	} `json:"ingredients"`
	SubRecipes map[string]struct {
		Title       string `json:"title"`
		Ingredients map[string]struct {
			Amount float64 `json:"amount"`
		} `json:"ingredients"`
		Steps []struct {
			ID     string   `json:"id"`
			Type   string   `json:"type"`
			Action string   `json:"action"`
			Time   string   `json:"time"`
			Tools  []string `json:"tools"`
			Inputs []struct {
				Type string `json:"type"`
				Ref  string `json:"ref"`
			} `json:"inputs"`
			Output struct {
				State       string `json:"state"`
				Description string `json:"description"`
			} `json:"output"`
		} `json:"steps"`
	} `json:"subRecipes"`
}

func toRecipeResponse(uiRecipe *models.UIRecipe, slug string) *RecipeResponse {
	return &RecipeResponse{
		Title:       uiRecipe.Title,
		Description: uiRecipe.Description,
		Servings:    uiRecipe.Servings,
		Difficulty:  uiRecipe.Difficulty,
		TotalTime:   uiRecipe.TotalTime,
		Image:       uiRecipe.Image,
		Slug:        slug,
		Metadata: struct {
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
		}{
			Description: uiRecipe.Description,
			Servings:    uiRecipe.Servings,
			Difficulty:  uiRecipe.Difficulty,
			TotalTime:   uiRecipe.TotalTime,
			Image:       uiRecipe.Image,
			ImageUrl:    uiRecipe.ImageUrl,
			SourceUrl:   uiRecipe.SourceUrl,
			Diet:        uiRecipe.Diet,
			Season:      uiRecipe.Season,
			RecipeType:  uiRecipe.RecipeType,
			Quick:       uiRecipe.Quick,
		},
		Ingredients: uiRecipe.Ingredients,
		SubRecipes:  uiRecipe.SubRecipes,
	}
}

func getAllRecipes(w http.ResponseWriter, r *http.Request) {
	startTime := time.Now()
	defer func() {
		log.Info().Dur("duration", time.Since(startTime)).Msg("GET /api/recipes")
	}()

	// Lire le contenu du dossier data
	files, err := os.ReadDir(dataDir)
	if err != nil {
		log.Error().Err(err).Msg("Error reading data directory")
		http.Error(w, "Error reading recipes", http.StatusInternalServerError)
		return
	}

	var recipes []*RecipeResponse

	// Parcourir les fichiers
	for _, file := range files {
		// Ne traiter que les fichiers .recipe.json
		if !strings.HasSuffix(file.Name(), ".recipe.json") {
			continue
		}

		// Extraire le slug du nom de fichier
		slug := strings.TrimSuffix(file.Name(), ".recipe.json")

		// Lire le contenu du fichier
		filePath := filepath.Join(dataDir, file.Name())
		content, err := os.ReadFile(filePath)
		if err != nil {
			log.Error().Err(err).Str("file", filePath).Msg("Error reading recipe file")
			continue
		}

		// Décoder le JSON
		var recipe models.Recipe
		if err := json.Unmarshal(content, &recipe); err != nil {
			log.Error().Err(err).Str("file", filePath).Msg("Error parsing recipe JSON")
			continue
		}

		// Convertir la recette au format UI puis au format de réponse
		uiRecipe := recipe.ConvertToUIRecipe()
		recipes = append(recipes, toRecipeResponse(uiRecipe, slug))
	}

	// Envoyer la réponse
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(recipes)
}

func getRecipeBySlug(w http.ResponseWriter, r *http.Request) {
	startTime := time.Now()
	defer func() {
		log.Info().Dur("duration", time.Since(startTime)).Msg("GET /api/recipes/{slug}")
	}()

	vars := mux.Vars(r)
	slug := vars["slug"]

	// Construire le chemin du fichier
	filePath := filepath.Join(dataDir, slug+".recipe.json")

	// Vérifier si le fichier existe
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		log.Error().Str("slug", slug).Msg("Recipe not found")
		http.NotFound(w, r)
		return
	}

	// Lire le contenu du fichier
	content, err := os.ReadFile(filePath)
	if err != nil {
		log.Error().Err(err).Str("file", filePath).Msg("Error reading recipe file")
		http.Error(w, "Error reading recipe", http.StatusInternalServerError)
		return
	}

	// Décoder le JSON
	var recipe models.Recipe
	if err := json.Unmarshal(content, &recipe); err != nil {
		log.Error().Err(err).Str("file", filePath).Msg("Error parsing recipe JSON")
		http.Error(w, "Error parsing recipe", http.StatusInternalServerError)
		return
	}

	// Convertir la recette au format UI puis au format de réponse
	uiRecipe := recipe.ConvertToUIRecipe()
	response := toRecipeResponse(uiRecipe, slug)

	// Envoyer la réponse
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		if !strings.HasPrefix(r.URL.Path, "/api") {
			return
		}
		duration := time.Since(start)
		log.Printf("%s %s - %s", r.Method, r.URL.Path, duration)
	})
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	// Charger les variables d'environnement
	if err := godotenv.Load(); err != nil {
		log.Warn().Err(err).Msg("Error loading .env file")
	}

	// Initialiser les services
	recipeService := services.NewRecipeService(dataDir)

	r := mux.NewRouter()

	// Middleware pour le logging
	r.Use(loggingMiddleware)
	r.Use(corsMiddleware)

	// Routes API
	api := r.PathPrefix("/api").Subrouter()

	// Route /recipes qui retourne la liste des recettes
	api.HandleFunc("/recipes", func(w http.ResponseWriter, r *http.Request) {
		results, err := recipeService.GetRecipeList()
		if err != nil {
			log.Error().Err(err).Msg("Failed to get recipes")
			http.Error(w, fmt.Sprintf("Failed to get recipes: %v", err), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(results)
	}).Methods("GET", "OPTIONS")

	// Route avec paramètre {slug} doit être après les routes spécifiques
	api.HandleFunc("/recipes/{slug}", getRecipeBySlug).Methods("GET", "OPTIONS")

	api.HandleFunc("/recipes/url", func(w http.ResponseWriter, r *http.Request) {
		var req models.GenerateRecipeRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			log.Error().Err(err).Msg("Error decoding request")
			http.Error(w, "Invalid request", http.StatusBadRequest)
			return
		}

		recipe, err := recipeService.AddRecipeFromUrl(req.Source)
		if err != nil {
			log.Error().Err(err).Msg("Error generating recipe")
			http.Error(w, fmt.Sprintf("Error generating recipe: %v", err), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(recipe)
	}).Methods("POST", "OPTIONS")
	api.HandleFunc("/recipes", func(w http.ResponseWriter, r *http.Request) {
		startTime := time.Now()
		defer func() {
			log.Info().Dur("duration", time.Since(startTime)).Msg("POST /api/recipes")
		}()

		var req struct {
			Url string `json:"url"`
		}

		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			log.Error().Err(err).Msg("Error decoding request")
			http.Error(w, "Invalid request", http.StatusBadRequest)
			return
		}

		// Générer la recette à partir de l'URL
		recipe, err := recipeService.AddRecipeFromUrl(req.Url)
		if err != nil {
			log.Error().Err(err).Msg("Error generating recipe")
			http.Error(w, "Error generating recipe", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(recipe); err != nil {
			log.Error().Err(err).Msg("Error encoding response")
			http.Error(w, "Error encoding response", http.StatusInternalServerError)
			return
		}
	}).Methods("POST", "OPTIONS")

	// Route pour les images
	api.HandleFunc("/images/{size}/{filename}", serveImage).Methods("GET", "OPTIONS")
	api.HandleFunc("/images/{filename}", serveImage).Methods("GET", "OPTIONS")

	// Démarrer le serveur
	port := os.Getenv("PORT")
	if port == "" {
		port = "3001"
	}

	log.Info().Str("port", port).Msg("Starting server")
	handler := cors.New(cors.Options{
		AllowedOrigins: []string{"*"},
		AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders: []string{"Content-Type", "Authorization"},
	}).Handler(r)

	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      handler,
		ReadTimeout:  300 * time.Second,
		WriteTimeout: 300 * time.Second,
		IdleTimeout:  300 * time.Second,
	}

	if err := srv.ListenAndServe(); err != nil {
		log.Fatal().Err(err).Msg("Server failed to start")
	}
}
