package utils

import (
	"regexp"
	"strings"
)

func CreateSlug(input string) string {
	// Convertir en minuscules
	slug := strings.ToLower(input)
	
	// Remplacer les accents
	slug = removeAccents(slug)
	
	// Supprimer les caractères non alphanumériques
	reg := regexp.MustCompile("[^a-z0-9]+")
	slug = reg.ReplaceAllString(slug, "-")
	
	// Supprimer les tirets en début et fin
	slug = strings.Trim(slug, "-")
	
	return slug
}

func removeAccents(input string) string {
	// Tableau de remplacement des accents
	replacements := map[string]string{
		"à": "a", "â": "a", "ä": "a",
		"é": "e", "è": "e", "ê": "e", "ë": "e",
		"î": "i", "ï": "i",
		"ô": "o", "ö": "o",
		"ù": "u", "û": "u", "ü": "u",
		"ç": "c",
		"ñ": "n",
	}
	
	for accent, replacement := range replacements {
		input = strings.ReplaceAll(input, accent, replacement)
	}
	
	return input
}
