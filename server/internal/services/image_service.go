package services

import (
	"fmt"
	"image"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/disintegration/imaging"
	"github.com/kolesa-team/go-webp/encoder"
	"github.com/kolesa-team/go-webp/webp"
)

type ImageSize struct {
	Name   string
	Width  int
	Height int
}

type ImageService struct {
	baseDir    string
	imageSizes []ImageSize
	imageCache sync.Map
}

func NewImageService(baseDir string) *ImageService {
	imageSizes := []ImageSize{
		{Name: "thumbnail", Width: 200, Height: 200},
		{Name: "small", Width: 400, Height: 400},
		{Name: "medium", Width: 800, Height: 800},
		{Name: "large", Width: 1200, Height: 1200},
		{Name: "original", Width: 0, Height: 0},
	}

	return &ImageService{
		baseDir:    baseDir,
		imageSizes: imageSizes,
		imageCache: sync.Map{},
	}
}

func (s *ImageService) SetupImageDirectories() error {
	dirs := []string{"original", "large", "medium", "small", "thumbnail"}
	for _, dir := range dirs {
		path := filepath.Join(s.baseDir, dir)
		if err := os.MkdirAll(path, os.ModePerm); err != nil {
			return fmt.Errorf("failed to create directory %s: %v", path, err)
		}
	}
	return nil
}

func (s *ImageService) IsValidImageFormat(filename string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	validExtensions := map[string]bool{
		".jpg":  true,
		".jpeg": true,
		".png":  true,
		".gif":  true,
		".webp": true,
	}
	return validExtensions[ext]
}

func (s *ImageService) GetResizedImagePath(originalPath, sizeName string) (string, error) {
	// Trouver la taille demandée
	var targetSize ImageSize
	found := false
	for _, size := range s.imageSizes {
		if size.Name == sizeName {
			targetSize = size
			found = true
			break
		}
	}
	if !found {
		return "", fmt.Errorf("invalid size: %s", sizeName)
	}

	// Construire le chemin de l'image redimensionnée
	filename := filepath.Base(originalPath)
	filenameWithoutExt := strings.TrimSuffix(filename, filepath.Ext(filename))
	resizedPath := filepath.Join(s.baseDir, targetSize.Name, filenameWithoutExt+".webp")

	// Si l'image redimensionnée n'existe pas, la créer
	if _, err := os.Stat(resizedPath); os.IsNotExist(err) {
		resizedPath, err = s.ResizeImage(originalPath, targetSize)
		if err != nil {
			return "", fmt.Errorf("failed to resize image: %v", err)
		}
	}

	return resizedPath, nil
}

func (s *ImageService) ResizeImage(originalPath string, size ImageSize) (string, error) {
	cacheKey := fmt.Sprintf("%s-%s", originalPath, size.Name)

	if cachedPath, ok := s.imageCache.Load(cacheKey); ok {
		return cachedPath.(string), nil
	}

	// Charger l'image originale
	src, err := imaging.Open(originalPath)
	if err != nil {
		return "", fmt.Errorf("failed to open image: %v", err)
	}

	// Redimensionner l'image
	var resizedImage image.Image
	if size.Width > 0 && size.Height > 0 {
		resizedImage = imaging.Resize(src, size.Width, size.Height, imaging.Lanczos)
	} else {
		resizedImage = src
	}

	// Créer le chemin de sortie en WebP
	filename := filepath.Base(originalPath)
	filenameWithoutExt := strings.TrimSuffix(filename, filepath.Ext(filename))
	outputPath := filepath.Join(s.baseDir, size.Name, filenameWithoutExt+".webp")
	
	err = os.MkdirAll(filepath.Dir(outputPath), os.ModePerm)
	if err != nil {
		return "", fmt.Errorf("failed to create output directory: %v", err)
	}

	// Convertir en WebP
	f, err := os.Create(outputPath)
	if err != nil {
		return "", fmt.Errorf("failed to create output file: %v", err)
	}
	defer f.Close()

	options, err := encoder.NewLossyEncoderOptions(encoder.PresetDefault, 75)
	if err != nil {
		return "", fmt.Errorf("failed to create WebP encoder options: %v", err)
	}

	err = webp.Encode(f, resizedImage, options)
	if err != nil {
		return "", fmt.Errorf("failed to encode WebP: %v", err)
	}

	// Mettre en cache le chemin
	s.imageCache.Store(cacheKey, outputPath)

	return outputPath, nil
}
