package services

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/blevesearch/bleve/v2"
	"github.com/blevesearch/bleve/v2/analysis/lang/fr"
	"github.com/blevesearch/bleve/v2/mapping"
	"github.com/rs/zerolog/log"
)

type SearchService struct {
	index    bleve.Index
	dataDir  string
	indexDir string
	mu       sync.RWMutex
}

type RecipeDocument struct {
	Title       string   `json:"title"`
	Description string   `json:"description"`
	Ingredients []string `json:"ingredients"`
	Categories  []string `json:"categories"`
	Slug        string   `json:"slug"`
}

func NewSearchService(dataDir string) (*SearchService, error) {
	indexDir := filepath.Join(dataDir, "search_index")
	
	// Créer le dossier pour l'index s'il n'existe pas
	if err := os.MkdirAll(indexDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create index directory: %v", err)
	}

	indexPath := filepath.Join(indexDir, "recipes.bleve")
	
	var index bleve.Index

	// Ouvrir l'index existant ou en créer un nouveau
	if _, err := os.Stat(indexPath); os.IsNotExist(err) {
		// Créer une configuration d'indexation en français
		indexMapping := bleve.NewIndexMapping()
		frenchAnalyzer := fr.AnalyzerName // Utiliser l'analyseur français
		
		// Configurer les champs
		docMapping := bleve.NewDocumentMapping()
		
		// Titre
		titleFieldMapping := mapping.NewTextFieldMapping()
		titleFieldMapping.Analyzer = frenchAnalyzer
		titleFieldMapping.Store = true
		titleFieldMapping.IncludeTermVectors = true
		titleFieldMapping.IncludeInAll = true
		docMapping.AddFieldMappingsAt("title", titleFieldMapping)
		
		// Description
		descFieldMapping := mapping.NewTextFieldMapping()
		descFieldMapping.Analyzer = frenchAnalyzer
		descFieldMapping.Store = true
		descFieldMapping.IncludeTermVectors = true
		descFieldMapping.IncludeInAll = true
		docMapping.AddFieldMappingsAt("description", descFieldMapping)
		
		// Ingrédients
		ingFieldMapping := mapping.NewTextFieldMapping()
		ingFieldMapping.Analyzer = frenchAnalyzer
		ingFieldMapping.Store = true
		ingFieldMapping.IncludeTermVectors = true
		ingFieldMapping.IncludeInAll = true
		docMapping.AddFieldMappingsAt("ingredients", ingFieldMapping)
		
		// Catégories
		catFieldMapping := mapping.NewTextFieldMapping()
		catFieldMapping.Analyzer = frenchAnalyzer
		catFieldMapping.Store = true
		catFieldMapping.IncludeTermVectors = true
		catFieldMapping.IncludeInAll = true
		docMapping.AddFieldMappingsAt("categories", catFieldMapping)

		// Slug
		slugFieldMapping := mapping.NewKeywordFieldMapping()
		slugFieldMapping.Store = true
		docMapping.AddFieldMappingsAt("slug", slugFieldMapping)

		// Configurer l'analyseur par défaut
		indexMapping.DefaultAnalyzer = frenchAnalyzer
		indexMapping.DefaultMapping = docMapping
		indexMapping.AddDocumentMapping("recipe", docMapping)
		
		var err error
		index, err = bleve.New(indexPath, indexMapping)
		if err != nil {
			return nil, fmt.Errorf("failed to create search index: %v", err)
		}
	} else {
		var err error
		index, err = bleve.Open(indexPath)
		if err != nil {
			return nil, fmt.Errorf("failed to open search index: %v", err)
		}
	}

	return &SearchService{
		index:    index,
		dataDir:  dataDir,
		indexDir: indexDir,
	}, nil
}

func (s *SearchService) IndexRecipe(recipe map[string]interface{}) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	// Extraire les ingrédients et catégories
	var ingredients []string
	var categories []string
	
	if ings, ok := recipe["ingredients"].([]interface{}); ok {
		for _, ing := range ings {
			if ingMap, ok := ing.(map[string]interface{}); ok {
				if name, ok := ingMap["name"].(string); ok {
					ingredients = append(ingredients, name)
				}
				if cat, ok := ingMap["category"].(string); ok && cat != "" {
					categories = append(categories, cat)
				}
			}
		}
	}

	// Créer un document avec le titre répété pour augmenter son poids
	title := fmt.Sprintf("%v", recipe["title"])
	description := fmt.Sprintf("%v", recipe["description"])
	slug := fmt.Sprintf("%v", recipe["slug"])
	
	// Répéter le titre et la description pour simuler un boost
	searchText := strings.Repeat(title+" ", 10) + " " + // Boost x10 pour le titre
		strings.Repeat(description+" ", 5) + " " + // Boost x5 pour la description
		strings.Join(ingredients, " ") + " " + 
		strings.Join(categories, " ")

	doc := RecipeDocument{
		Title:       title,
		Description: description,
		Ingredients: ingredients,
		Categories:  categories,
		Slug:        slug,
	}

	// Indexer à la fois le document et le texte de recherche
	if err := s.index.Index(doc.Slug+"_doc", doc); err != nil {
		return err
	}
	
	return s.index.Index(doc.Slug+"_search", struct {
		Text string `json:"text"`
	}{
		Text: searchText,
	})
}

func (s *SearchService) Search(query string) ([]map[string]interface{}, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	log.Info().Str("query", query).Msg("Searching recipes")

	// Créer une requête qui combine plusieurs champs avec différents poids
	titleQuery := bleve.NewMatchQuery(query)
	titleQuery.SetField("title")
	titleQuery.SetBoost(3.0)
	titleQuery.SetFuzziness(1)

	descQuery := bleve.NewMatchQuery(query)
	descQuery.SetField("description")
	descQuery.SetBoost(2.0)
	descQuery.SetFuzziness(1)

	ingQuery := bleve.NewMatchQuery(query)
	ingQuery.SetField("ingredients")
	ingQuery.SetBoost(1.5)
	ingQuery.SetFuzziness(1)

	// Combiner les requêtes avec un OU
	q := bleve.NewDisjunctionQuery(titleQuery, descQuery, ingQuery)
	
	search := bleve.NewSearchRequest(q)
	search.Fields = []string{"title", "description", "ingredients", "categories", "slug"}
	search.Size = 20 // Limiter à 20 résultats

	searchResults, err := s.index.Search(search)
	if err != nil {
		log.Error().Err(err).Msg("Search failed")
		return nil, fmt.Errorf("search failed: %v", err)
	}

	log.Info().Int("total_hits", len(searchResults.Hits)).Msg("Search completed")

	var results []map[string]interface{}
	for _, hit := range searchResults.Hits {
		log.Debug().
			Str("id", hit.ID).
			Float64("score", hit.Score).
			Interface("fields", hit.Fields).
			Msg("Processing search hit")

		// Utiliser l'ID du document comme slug
		result := map[string]interface{}{
			"slug":  hit.ID,
			"title": hit.Fields["title"],
			"score": hit.Score,
		}

		// Ajouter les catégories si elles existent
		if categories, ok := hit.Fields["categories"].([]interface{}); ok && len(categories) > 0 {
			result["categories"] = categories
		}
		
		results = append(results, result)
	}

	// Ajouter un tableau vide si aucun résultat n'est trouvé
	if len(results) == 0 {
		log.Info().Msg("No results found")
		return []map[string]interface{}{}, nil
	}

	return results, nil
}

func (s *SearchService) RebuildIndex() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	log.Info().Msg("Starting index rebuild...")

	// Créer un dossier temporaire pour le nouvel index
	tempIndexDir := filepath.Join(s.indexDir, "temp")
	if err := os.MkdirAll(tempIndexDir, 0755); err != nil {
		return fmt.Errorf("failed to create temp index directory: %v", err)
	}
	defer os.RemoveAll(tempIndexDir) // Nettoyer le dossier temporaire à la fin

	// Créer un nouvel index dans le dossier temporaire
	tempIndexPath := filepath.Join(tempIndexDir, "recipes.bleve")
	
	// Créer une configuration d'indexation en français
	indexMapping := bleve.NewIndexMapping()
	frenchAnalyzer := fr.AnalyzerName // Utiliser l'analyseur français
	
	// Configurer les champs
	docMapping := bleve.NewDocumentMapping()
	
	// Titre
	titleFieldMapping := mapping.NewTextFieldMapping()
	titleFieldMapping.Analyzer = frenchAnalyzer
	titleFieldMapping.Store = true
	titleFieldMapping.IncludeTermVectors = true
	titleFieldMapping.IncludeInAll = true
	docMapping.AddFieldMappingsAt("title", titleFieldMapping)
	
	// Description
	descFieldMapping := mapping.NewTextFieldMapping()
	descFieldMapping.Analyzer = frenchAnalyzer
	descFieldMapping.Store = true
	descFieldMapping.IncludeTermVectors = true
	descFieldMapping.IncludeInAll = true
	docMapping.AddFieldMappingsAt("description", descFieldMapping)
	
	// Ingrédients
	ingFieldMapping := mapping.NewTextFieldMapping()
	ingFieldMapping.Analyzer = frenchAnalyzer
	ingFieldMapping.Store = true
	ingFieldMapping.IncludeTermVectors = true
	ingFieldMapping.IncludeInAll = true
	docMapping.AddFieldMappingsAt("ingredients", ingFieldMapping)
	
	// Catégories
	catFieldMapping := mapping.NewTextFieldMapping()
	catFieldMapping.Analyzer = frenchAnalyzer
	catFieldMapping.Store = true
	catFieldMapping.IncludeTermVectors = true
	catFieldMapping.IncludeInAll = true
	docMapping.AddFieldMappingsAt("categories", catFieldMapping)

	// Slug
	slugFieldMapping := mapping.NewKeywordFieldMapping()
	slugFieldMapping.Store = true
	docMapping.AddFieldMappingsAt("slug", slugFieldMapping)

	// Configurer l'analyseur par défaut
	indexMapping.DefaultAnalyzer = frenchAnalyzer
	indexMapping.DefaultMapping = docMapping
	indexMapping.AddDocumentMapping("recipe", docMapping)

	log.Info().Msg("Creating new index...")
	newIndex, err := bleve.New(tempIndexPath, indexMapping)
	if err != nil {
		return fmt.Errorf("failed to create new index: %v", err)
	}

	// Réindexer toutes les recettes dans le nouvel index
	files, err := os.ReadDir(s.dataDir)
	if err != nil {
		newIndex.Close()
		return fmt.Errorf("failed to read data directory: %v", err)
	}

	log.Info().Int("total_files", len(files)).Msg("Found recipe files")
	indexedCount := 0

	for _, file := range files {
		if file.IsDir() || !strings.HasSuffix(file.Name(), ".recipe.json") {
			continue
		}

		log.Debug().Str("file", file.Name()).Msg("Processing recipe file")

		data, err := os.ReadFile(filepath.Join(s.dataDir, file.Name()))
		if err != nil {
			newIndex.Close()
			return fmt.Errorf("failed to read recipe file %s: %v", file.Name(), err)
		}

		var recipe map[string]interface{}
		if err := json.Unmarshal(data, &recipe); err != nil {
			newIndex.Close()
			return fmt.Errorf("failed to parse recipe file %s: %v", file.Name(), err)
		}

		// Extraire les métadonnées
		metadata, ok := recipe["metadata"].(map[string]interface{})
		if !ok {
			newIndex.Close()
			return fmt.Errorf("invalid metadata in recipe file %s", file.Name())
		}

		title := fmt.Sprintf("%v", metadata["title"])
		description := fmt.Sprintf("%v", metadata["description"])
		slug := strings.TrimSuffix(file.Name(), ".recipe.json")
		
		var ingredients []string
		if ingredientsList, ok := recipe["ingredientsList"].([]interface{}); ok {
			for _, ing := range ingredientsList {
				if ingMap, ok := ing.(map[string]interface{}); ok {
					if name, ok := ingMap["name"].(string); ok {
						ingredients = append(ingredients, name)
					}
				}
			}
		}

		doc := RecipeDocument{
			Title:       title,
			Description: description,
			Ingredients: ingredients,
			Categories:  []string{}, // TODO: ajouter les catégories si nécessaire
			Slug:        slug,
		}

		log.Debug().
			Str("title", title).
			Str("slug", slug).
			Int("ingredients_count", len(ingredients)).
			Msg("Indexing recipe")

		if err := newIndex.Index(slug, doc); err != nil {
			newIndex.Close()
			return fmt.Errorf("failed to index recipe document %s: %v", file.Name(), err)
		}

		indexedCount++
	}

	log.Info().Int("indexed_count", indexedCount).Msg("Finished indexing recipes")

	// Fermer l'ancien index
	oldIndex := s.index
	s.index = newIndex

	// Déplacer le nouvel index à la place de l'ancien
	oldIndexPath := filepath.Join(s.indexDir, "recipes.bleve")
	if err := oldIndex.Close(); err != nil {
		return fmt.Errorf("failed to close old index: %v", err)
	}
	
	if err := os.RemoveAll(oldIndexPath); err != nil {
		return fmt.Errorf("failed to remove old index: %v", err)
	}
	
	if err := os.Rename(tempIndexPath, oldIndexPath); err != nil {
		return fmt.Errorf("failed to move new index: %v", err)
	}

	log.Info().Msg("Successfully rebuilt search index")
	return nil
}
