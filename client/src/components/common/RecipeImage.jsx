import React, { useEffect, useState, useMemo } from "react";
import { Box } from "@mui/material";
import KitchenOutlinedIcon from "@mui/icons-material/KitchenOutlined";

const API_BASE_URL =
  import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

const PlaceholderBox = React.memo(() => (
  <Box
    sx={{
      width: "100%",
      height: "100%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      bgcolor: "background.default",
      color: "text.secondary",
      position: "absolute",
      top: 0,
      left: 0,
    }}
  >
    <KitchenOutlinedIcon sx={{ fontSize: 48 }} />
  </Box>
));

const RecipeImage = ({ slug, title, size = "medium", sx = {}, onLoad }) => {
  const [status, setStatus] = useState("loading"); // "loading", "loaded", "error"

  // Mémoriser l'URL de l'image
  const imageUrl = useMemo(() => {
    return slug ? `${API_BASE_URL}/api/images/${size}/${slug}` : null;
  }, [slug, size]);

  useEffect(() => {
    // Réinitialiser l'état uniquement si l'URL change
    if (!imageUrl) {
      setStatus("error");
      return;
    }

    setStatus("loading");

    // Utiliser une technique de préchargement avec délai minimal pour éviter le flickering
    const img = new Image();

    // Un petit délai pour éviter les changements visuels trop rapides
    const loadTimer = setTimeout(() => {
      img.onload = () => {
        setStatus("loaded");
        if (onLoad) {
          onLoad(img.naturalWidth / img.naturalHeight);
        }
      };
      img.onerror = () => setStatus("error");

      // Définir la source après avoir attaché les gestionnaires d'événements
      img.src = imageUrl;
    }, 50);

    return () => {
      clearTimeout(loadTimer);
      img.onload = null;
      img.onerror = null;
    };
  }, [imageUrl, onLoad]);

  // Utiliser un rendu conditionnel simple pour éviter les transitions inutiles
  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        ...sx,
      }}
    >
      {status === "loaded" ? (
        <Box
          component="img"
          src={imageUrl}
          alt={title || ""}
          sx={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity: 1,
            // Transition douce lorsque l'image apparaît
            animation: "fadeIn 0.3s ease-in-out",
            "@keyframes fadeIn": {
              from: { opacity: 0 },
              to: { opacity: 1 },
            },
          }}
        />
      ) : (
        <PlaceholderBox />
      )}
    </Box>
  );
};

// Exporter le composant avec React.memo pour éviter les re-rendus inutiles
// et une fonction de comparaison personnalisée pour des performances optimales
export default React.memo(RecipeImage, (prevProps, nextProps) => {
  return prevProps.slug === nextProps.slug && prevProps.size === nextProps.size;
});
