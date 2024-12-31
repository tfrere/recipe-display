package main

import (
	"encoding/json"
	"os"
	"path/filepath"
)

func main() {
	// Chemin du dossier contenant les fichiers HTML
	htmlDir := "/Users/frerethibaud/Documents/personal-projects/ottolenghi-recipes/recipes/data/html"
	
	// Chemin du fichier de sortie JSON
	outputFile := "/Users/frerethibaud/Documents/personal-projects/recipe-display/server/cmd/tools/sources/tfrere-ottolenghi_recipes.json"

	// Liste tous les fichiers HTML
	var files []string
	err := filepath.Walk(htmlDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && filepath.Ext(path) == ".html" {
			// Obtenir le chemin relatif par rapport au dossier HTML
			relPath, err := filepath.Rel(htmlDir, path)
			if err != nil {
				return err
			}
			files = append(files, relPath)
		}
		return nil
	})
	if err != nil {
		panic(err)
	}

	// Crée le dossier de sortie s'il n'existe pas
	os.MkdirAll(filepath.Dir(outputFile), 0755)

	// Convertit en JSON et sauvegarde
	jsonData, err := json.MarshalIndent(files, "", "  ")
	if err != nil {
		panic(err)
	}

	err = os.WriteFile(outputFile, jsonData, 0644)
	if err != nil {
		panic(err)
	}
}
