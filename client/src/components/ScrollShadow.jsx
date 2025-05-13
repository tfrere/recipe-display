import React, { useState, useEffect } from "react";
import { useTheme } from "@mui/material";

/**
 * Composant qui affiche un gradient en haut d'un conteneur de défilement
 * seulement quand l'utilisateur a scrollé vers le bas
 */
const ScrollShadow = ({ scrollRef, height = 16, shadowColor = null }) => {
  const theme = useTheme();
  const [isScrolled, setIsScrolled] = useState(false);

  // Augmenter contraste pour meilleure visibilité
  const darkColor =
    theme.palette.mode === "dark" ? "rgba(0, 0, 0, 0.3)" : "rgba(0, 0, 0, 0.1)";

  useEffect(() => {
    const scrollElement = scrollRef.current;
    if (!scrollElement) return;

    const handleScroll = () => {
      setIsScrolled(scrollElement.scrollTop > 5);
    };

    // Vérifier l'état initial
    handleScroll();

    // Ajouter l'écouteur d'événement
    scrollElement.addEventListener("scroll", handleScroll);

    // Nettoyer l'écouteur d'événement
    return () => {
      scrollElement.removeEventListener("scroll", handleScroll);
    };
  }, [scrollRef]);

  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        left: 0,
        right: 0,
        height: `${height}px`,
        background: `linear-gradient(${darkColor}, transparent)`,
        opacity: isScrolled ? 1 : 0,
        zIndex: 999,
        pointerEvents: "none",
        transition: "opacity 0.2s ease",
      }}
    />
  );
};

export default ScrollShadow;
