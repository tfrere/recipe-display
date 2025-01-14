import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const preloadImage = (src) =>
  new Promise((resolve, reject) => {
    const img = new Image();
    img.src = src;
    img.onload = () => resolve(src);
    img.onerror = () => reject(new Error(`Failed to load image: ${src}`));
  });

const useImagePreloader = (slug, size = 'medium') => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!slug) {
      setIsLoaded(true);
      return;
    }

    setIsLoaded(false);
    setError(null);

    const imageUrl = `${API_BASE_URL}/api/images/${size}/${slug}`;

    preloadImage(imageUrl)
      .then(() => {
        setIsLoaded(true);
      })
      .catch((err) => {
        console.error('Error preloading image:', err);
        setError(err);
        // On considère l'image comme chargée même en cas d'erreur pour ne pas bloquer l'interface
        setIsLoaded(true);
      });
  }, [slug, size]);

  return { isLoaded, error };
};

export default useImagePreloader;
