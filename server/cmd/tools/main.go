package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

func clearDatabase() error {
	// Chemin vers le dossier data
	dataDir := filepath.Join(".", "data")

	// Supprimer tous les fichiers .recipe.json
	recipes, err := filepath.Glob(filepath.Join(dataDir, "*.recipe.json"))
	if err != nil {
		return fmt.Errorf("error finding recipe files: %w", err)
	}
	for _, recipe := range recipes {
		if err := os.Remove(recipe); err != nil {
			return fmt.Errorf("error removing recipe file %s: %w", recipe, err)
		}
		fmt.Printf("Removed recipe file: %s\n", recipe)
	}

	// Supprimer toutes les images de manière récursive
	imagesDir := filepath.Join(dataDir, "images")
	err = filepath.Walk(imagesDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		// Ne supprimer que les fichiers, pas les dossiers
		if !info.IsDir() {
			if err := os.Remove(path); err != nil {
				return fmt.Errorf("error removing image file %s: %w", path, err)
			}
			fmt.Printf("Removed image file: %s\n", path)
		}
		return nil
	})
	if err != nil {
		return fmt.Errorf("error walking through images directory: %w", err)
	}

	fmt.Println("Database cleared successfully!")
	return nil
}

func importRecipes(filename string, limit int) error {
	// Utiliser directement le chemin fourni
	if _, err := os.Stat(filename); os.IsNotExist(err) {
		return fmt.Errorf("file not found: %s", filename)
	}
	
	content, err := os.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("error reading recipes file: %w", err)
	}

	var urls []string
	if err := json.Unmarshal(content, &urls); err != nil {
		return fmt.Errorf("error parsing recipes file: %w", err)
	}

	// Limiter le nombre de recettes si demandé
	if limit > 0 && limit < len(urls) {
		fmt.Printf("Limiting import to %d recipes (out of %d available)\n", limit, len(urls))
		urls = urls[:limit]
	}

	client := &http.Client{
		Timeout: 300 * time.Second,
	}

	// Pour chaque URL, envoyer une requête POST à l'API
	for i, url := range urls {
		fmt.Printf("Importing recipe %d/%d: %s\n", i+1, len(urls), url)

		// Préparer la requête
		reqBody := struct {
			URL string `json:"url"`
		}{
			URL: url,
		}
		jsonData, err := json.Marshal(reqBody)
		if err != nil {
			fmt.Printf("Error marshaling request for %s: %v\n", url, err)
			continue
		}

		// Envoyer la requête
		resp, err := client.Post("http://localhost:3001/api/recipes", "application/json", bytes.NewBuffer(jsonData))
		if err != nil {
			fmt.Printf("Error sending request for %s: %v\n", url, err)
			continue
		}

		// Lire la réponse
		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			fmt.Printf("Error reading response for %s: %v\n", url, err)
			continue
		}

		if resp.StatusCode == http.StatusConflict {
			fmt.Printf("Recipe already exists, skipping: %s\n", url)
			continue
		}

		if resp.StatusCode != http.StatusOK {
			fmt.Printf("Error response for %s: %s\n", url, body)
			continue
		}

		fmt.Printf("Successfully imported recipe from %s\n", url)
		
		// Attendre un peu entre chaque requête pour ne pas surcharger le serveur
		time.Sleep(1 * time.Second)
	}

	return nil
}

func main() {
	// Définir les sous-commandes
	clearCmd := flag.NewFlagSet("clear", flag.ExitOnError)
	importCmd := flag.NewFlagSet("import", flag.ExitOnError)

	// Ajouter les paramètres à la commande import
	importFile := importCmd.String("file", "data/experiments/tfrere-ottolenghi_recipes.json", "Path to JSON file containing recipe URLs")
	importLimit := importCmd.Int("limit", 0, "Limit the number of recipes to import (0 = no limit)")

	// Vérifier les arguments
	if len(os.Args) < 2 {
		fmt.Println("expected subcommand")
		fmt.Println("Available commands:")
		fmt.Println("  clear   - Clear the database")
		fmt.Println("  import  - Import recipes from a JSON file")
		fmt.Println("           Options:")
		fmt.Println("             -file PATH  Path to JSON file (default: data/experiments/tfrere-ottolenghi_recipes.json)")
		fmt.Println("             -limit N    Limit import to N recipes (default: 0 = no limit)")
		os.Exit(1)
	}

	// Parser la sous-commande
	switch os.Args[1] {
	case "clear":
		clearCmd.Parse(os.Args[2:])
		if err := clearDatabase(); err != nil {
			fmt.Printf("Error clearing database: %v\n", err)
			os.Exit(1)
		}
	case "import":
		importCmd.Parse(os.Args[2:])
		if err := importRecipes(*importFile, *importLimit); err != nil {
			fmt.Printf("Error importing recipes: %v\n", err)
			os.Exit(1)
		}
	default:
		fmt.Printf("unknown subcommand: %s\n", os.Args[1])
		fmt.Println("Available commands:")
		fmt.Println("  clear   - Clear the database")
		fmt.Println("  import  - Import recipes from a JSON file")
		fmt.Println("           Options:")
		fmt.Println("             -file PATH  Path to JSON file (default: data/experiments/tfrere-ottolenghi_recipes.json)")
		fmt.Println("             -limit N    Limit import to N recipes (default: 0 = no limit)")
		os.Exit(1)
	}
}
