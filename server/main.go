package main

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/mux"
	"github.com/rs/cors"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/joho/godotenv"

	"recipe-display/server/internal/models"
	"recipe-display/server/internal/services"
	"recipe-display/server/internal/utils"
)

var (
	// Mutex pour protéger l'accès aux fichiers
	fileMutex sync.Mutex

	imageCache = sync.Map{}
	imageSizes = []services.ImageSize{
		{Name: "thumbnail", Width: 200, Height: 200},
		{Name: "small", Width: 400, Height: 400},
		{Name: "medium", Width: 800, Height: 800},
		{Name: "large", Width: 1200, Height: 1200},
		{Name: "original", Width: 0, Height: 0},
	}
)

func init() {
	// Configure zerolog
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	zerolog.SetGlobalLevel(zerolog.InfoLevel)
}

func serveImage(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	size := vars["size"]
	filename := vars["filename"]

	imageService := services.NewImageService("./data/images")

	if !imageService.IsValidImageFormat(filename) {
		log.Printf("Invalid image format: %s", filename)
		http.Error(w, "Invalid image format", http.StatusBadRequest)
		return
	}

	originalPath := filepath.Join("./data/images/original", filename)
	resizedPath := originalPath

	// Si une taille est spécifiée, redimensionner l'image
	if size != "" {
		var err error
		resizedPath, err = imageService.GetResizedImagePath(originalPath, size)
		if err != nil {
			log.Printf("Error getting resized image path: %v", err)
			http.Error(w, "Failed to get resized image", http.StatusInternalServerError)
			return
		}
	}

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
	Ingredients map[string]struct {
		Name     string `json:"name"`
		Unit     string `json:"unit"`
		Category string `json:"category"`
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
	files, err := os.ReadDir("./data")
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
		filePath := filepath.Join("./data", file.Name())
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
	filePath := filepath.Join("./data", slug+".recipe.json")

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
		log.Error().Err(err).Msg("Error loading .env file")
	}

	// Créer le router
	r := mux.NewRouter()

	// Middleware CORS
	corsHandler := cors.New(cors.Options{
		AllowedOrigins: []string{"*"},
		AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders: []string{"Content-Type", "Authorization"},
	})

	// Middleware pour le logging
	r.Use(loggingMiddleware)
	r.Use(corsMiddleware)

	// Routes statiques
	r.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("static"))))
	r.HandleFunc("/images/{filename}", serveImage).Methods("GET")

	// Image routes
	r.HandleFunc("/api/images/{size}/{filename}", serveImage).Methods("GET")
	r.HandleFunc("/api/images/{filename}", serveImage).Methods("GET")

	// API endpoints
	r.HandleFunc("/api/recipes", getAllRecipes).Methods("GET")
	r.HandleFunc("/api/recipes/{slug}", getRecipeBySlug).Methods("GET")

	// Generate recipe endpoint
	r.HandleFunc("/api/recipes/generate", func(w http.ResponseWriter, r *http.Request) {
		startTime := time.Now()
		defer func() {
			log.Info().Dur("duration", time.Since(startTime)).Msg("POST /api/recipes/generate")
		}()

		var req struct {
			Prompt string `json:"prompt"`
		}

		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			log.Error().Err(err).Msg("Error decoding request")
			http.Error(w, "Invalid request", http.StatusBadRequest)
			return
		}

		uiRecipe, err := utils.GenerateRecipe(req.Prompt)
		if err != nil {
			log.Error().Err(err).Msg("Error generating recipe")
			http.Error(w, "Error generating recipe", http.StatusInternalServerError)
			return
		}

		// Vérifier que le titre n'est pas vide
		if uiRecipe.Title == "" {
			log.Error().Msg("Generated recipe has no title")
			http.Error(w, "Generated recipe has no title", http.StatusInternalServerError)
			return
		}

		// Créer le slug à partir du titre
		slug := utils.CreateSlug(uiRecipe.Title)
		
		// Utiliser le chemin absolu pour le dossier data
		dataDir := "data"
		if !filepath.IsAbs(dataDir) {
			// Si on est en développement, on utilise le chemin relatif au répertoire de travail
			wd, err := os.Getwd()
			if err != nil {
				log.Error().Err(err).Msg("Error getting working directory")
				http.Error(w, "Error saving recipe", http.StatusInternalServerError)
				return
			}
			dataDir = filepath.Join(wd, dataDir)
		}
		filePath := filepath.Join(dataDir, slug+".recipe.json")

		log.Info().Str("path", filePath).Msg("Saving recipe to")

		// Vérifier si le fichier existe déjà
		if _, err := os.Stat(filePath); err == nil {
			log.Error().Str("path", filePath).Msg("Recipe file already exists")
			http.Error(w, "Recipe already exists", http.StatusConflict)
			return
		}

		// Convertir la recette générée en format Recipe
		recipe := &models.Recipe{
			Metadata: struct {
				Title       string `json:"title"`
				Description string `json:"description"`
				Servings    int    `json:"servings"`
				Difficulty  string `json:"difficulty"`
				TotalTime   string `json:"totalTime"`
				Image       string `json:"image"`
				ImageUrl    string `json:"imageUrl"`
				SourceUrl   string `json:"sourceUrl"`
			}{
				Title:       uiRecipe.Title,
				Description: uiRecipe.Description,
				Servings:    uiRecipe.Servings,
				Difficulty:  uiRecipe.Difficulty,
				TotalTime:   uiRecipe.TotalTime,
				Image:       uiRecipe.Image,
				ImageUrl:    "", // Sera rempli par GPT-4
				SourceUrl:   "", // Sera rempli par GPT-4
			},
		}

		// Convertir les ingrédients
		for id, ing := range uiRecipe.Ingredients {
			recipe.IngredientsList = append(recipe.IngredientsList, struct {
				ID     string  `json:"id"`
				Name   string  `json:"name"`
				Unit   string  `json:"unit"`
				Amount float64 `json:"amount"`
			}{
				ID:   id,
				Name: ing.Name,
				Unit: ing.Unit,
			})
		}

		// Convertir les sous-recettes
		for id, sub := range uiRecipe.SubRecipes {
			// Convertir les steps
			var steps []struct {
				ID     string   `json:"id"`
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
			}

			for _, step := range sub.Steps {
				steps = append(steps, struct {
					ID     string   `json:"id"`
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
				}{
					ID:     step.ID,
					Action: step.Action,
					Time:   step.Time,
					Tools:  step.Tools,
					Inputs: step.Inputs,
					Output: step.Output,
				})
			}

			subRecipe := struct {
				ID    string `json:"id"`
				Title string `json:"title"`
				Steps []struct {
					ID     string   `json:"id"`
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
			}{
				ID:    id,
				Title: sub.Title,
				Steps: steps,
			}
			recipe.SubRecipes = append(recipe.SubRecipes, subRecipe)

			// Ajouter les quantités aux ingrédients
			for ingID, amount := range sub.Ingredients {
				for i, ing := range recipe.IngredientsList {
					if ing.ID == ingID {
						recipe.IngredientsList[i].Amount = amount.Amount
						break
					}
				}
			}
		}

		// Sauvegarder la recette dans un fichier
		file, err := json.MarshalIndent(recipe, "", "  ")
		if err != nil {
			log.Error().Err(err).Msg("Error marshaling recipe")
			http.Error(w, "Error saving recipe", http.StatusInternalServerError)
			return
		}

		// S'assurer que le dossier existe
		if err := os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
			log.Error().Err(err).Msg("Error creating data directory")
			http.Error(w, "Error saving recipe", http.StatusInternalServerError)
			return
		}

		if err := os.WriteFile(filePath, file, 0644); err != nil {
			log.Error().Err(err).Msg("Error writing recipe file")
			http.Error(w, "Error saving recipe", http.StatusInternalServerError)
			return
		}

		log.Info().Str("path", filePath).Msg("Recipe saved successfully")

		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(recipe); err != nil {
			log.Error().Err(err).Msg("Error encoding response")
			http.Error(w, "Error encoding response", http.StatusInternalServerError)
			return
		}
	}).Methods("POST")

	// Démarrer le serveur
	port := os.Getenv("PORT")
	if port == "" {
		port = "3001"
	}

	log.Info().Str("port", port).Msg("Starting server")
	handler := corsHandler.Handler(r)
	
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
