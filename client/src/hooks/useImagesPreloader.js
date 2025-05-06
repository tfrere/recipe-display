import { useState, useEffect, useRef } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

const preloadImage = (src) =>
  new Promise((resolve, reject) => {
    const img = new Image();
    img.src = src;
    img.onload = () => resolve(src);
    img.onerror = () => reject(new Error(`Failed to load image: ${src}`));
  });

const useImagesPreloader = (slugs = [], size = "medium") => {
  const [loadedImages, setLoadedImages] = useState(new Set());
  const [errors, setErrors] = useState({});
  const loadedRef = useRef(new Set());

  // Réinitialiser le cache d'images lorsque slugs change complètement
  useEffect(() => {
    // Si les slugs changent complètement (nouvelle recette), on réinitialise tout
    if (
      slugs.length === 0 ||
      (slugs.length === 1 && !loadedRef.current.has(slugs[0]))
    ) {
      setLoadedImages(new Set());
      setErrors({});
      loadedRef.current = new Set();
    }
  }, [slugs]);

  useEffect(() => {
    if (slugs.length === 0) {
      return;
    }

    const loadImage = async (slug) => {
      // Si l'image est déjà chargée, ne pas la recharger
      if (loadedRef.current.has(slug)) {
        return;
      }

      try {
        const imageUrl = `${API_BASE_URL}/api/images/${size}/${slug}`;
        await preloadImage(imageUrl);
        loadedRef.current.add(slug);
        // Mettre à jour loadedImages une seule fois après le chargement de toutes les images
      } catch (err) {
        console.error("Error preloading image:", err);
        setErrors((prev) => ({ ...prev, [slug]: err.message }));
        // On considère l'image comme chargée même en cas d'erreur
        loadedRef.current.add(slug);
      }
    };

    // Charger uniquement les nouvelles images
    const newSlugs = slugs.filter((slug) => !loadedRef.current.has(slug));

    if (newSlugs.length > 0) {
      // Réinitialiser les erreurs pour les nouvelles images uniquement
      setErrors((prev) => {
        const next = { ...prev };
        newSlugs.forEach((slug) => delete next[slug]);
        return next;
      });

      // Charger les nouvelles images
      Promise.all(newSlugs.map(loadImage)).then(() => {
        setLoadedImages(new Set(loadedRef.current));
      });
    }
  }, [slugs, size]);

  return {
    isLoaded: (slug) => loadedRef.current.has(slug),
    allLoaded:
      slugs.length === 0 || slugs.every((slug) => loadedRef.current.has(slug)),
    errors,
  };
};

export default useImagesPreloader;
