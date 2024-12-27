package main

import (
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"

	"golang.org/x/net/html"
)

func fetchWebPageContent(urlStr string) (string, error) {
	// Create a new HTTP client
	client := &http.Client{}

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

func extractWebpageContent(urlStr string, htmlContent string) string {
	doc, err := html.Parse(strings.NewReader(htmlContent))
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing HTML: %v\n", err)
		return ""
	}

	var extractText func(*html.Node) string
	extractText = func(n *html.Node) string {
		// Récupérer TOUT le texte, sans exception
		if n.Type == html.TextNode {
			return strings.TrimSpace(n.Data)
		}

		var text string
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			text += extractText(c) + " "
		}

		return text
	}

	var extractImages func(*html.Node) []string
	extractImages = func(n *html.Node) []string {
		var images []string
		if n.Type == html.ElementNode {
			// Chercher les balises img
			if n.Data == "img" {
				for _, a := range n.Attr {
					if a.Key == "src" {
						// Convertir les URLs relatives en absolues
						var imageUrl string
						if strings.HasPrefix(a.Val, "http://") || strings.HasPrefix(a.Val, "https://") {
							imageUrl = a.Val
						} else {
							// Convertir les URLs relatives
							base, err := url.Parse(urlStr)
							if err != nil {
								continue
							}
							
							rel, err := url.Parse(a.Val)
							if err != nil {
								continue
							}
							
							imageUrl = base.ResolveReference(rel).String()
						}

						if imageUrl != "" {
							images = append(images, imageUrl)
						}
					}
				}
			}
		}

		for c := n.FirstChild; c != nil; c = c.NextSibling {
			images = append(images, extractImages(c)...)
		}

		return images
	}

	text := extractText(doc)
	images := extractImages(doc)

	// Combiner le texte et les images
	result := fmt.Sprintf("Webpage Content:\n%s\n\nImages:\n%s", 
		text, 
		strings.Join(images, "\n"))

	return result
}

func main() {
	// Vérifier qu'une URL est fournie
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run webpage_extractor.go <url>")
		os.Exit(1)
	}

	// Récupérer l'URL depuis les arguments
	url := os.Args[1]

	// Récupérer le contenu de la page
	htmlContent, err := fetchWebPageContent(url)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error fetching webpage: %v\n", err)
		os.Exit(1)
	}

	// Extraire le contenu
	extractedContent := extractWebpageContent(url, htmlContent)

	// Afficher le résultat
	fmt.Println(extractedContent)
}
