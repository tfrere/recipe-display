package utils

import (
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
)

type WebContent struct {
	Title       string
	MainContent string
	ImageURLs   []string
}

func ExtractWebContent(html string) (*WebContent, error) {
	// Parse le HTML
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("error parsing HTML: %v", err)
	}

	content := &WebContent{
		ImageURLs: make([]string, 0),
	}

	// Extraire le titre
	content.Title = doc.Find("title").Text()

	// Extraire toutes les images (src et data-src)
	doc.Find("img").Each(func(i int, s *goquery.Selection) {
		// Vérifier src
		if src, exists := s.Attr("src"); exists && src != "" {
			content.ImageURLs = append(content.ImageURLs, src)
		}
		// Vérifier data-src (souvent utilisé pour le lazy loading)
		if dataSrc, exists := s.Attr("data-src"); exists && dataSrc != "" {
			content.ImageURLs = append(content.ImageURLs, dataSrc)
		}
		// Vérifier srcset
		if srcset, exists := s.Attr("srcset"); exists && srcset != "" {
			// Extraire les URLs du srcset
			urls := strings.Fields(srcset)
			for _, url := range urls {
				// Ignorer les descripteurs de taille (ex: 1x, 300w)
				if !strings.Contains(url, " ") && !strings.HasSuffix(url, "w") && !strings.HasSuffix(url, "x") {
					content.ImageURLs = append(content.ImageURLs, url)
				}
			}
		}
	})

	// Extraire tout le texte du body
	content.MainContent = doc.Find("body").Text()

	// Nettoyer le contenu
	content.MainContent = strings.TrimSpace(content.MainContent)
	content.Title = strings.TrimSpace(content.Title)

	return content, nil
}

func FetchWebPageContent(urlStr string) (string, error) {
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
