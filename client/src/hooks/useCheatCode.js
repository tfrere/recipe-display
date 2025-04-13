import { useEffect, useState, useRef, useCallback } from "react";
import useLocalStorage from "./useLocalStorage";

// Définition du cheat code : gauche, bas, droite, haut, gauche, bas, droite, haut
const CHEAT_CODE = [
  "ArrowLeft",
  "ArrowDown",
  "ArrowRight",
  "ArrowUp",
  "ArrowLeft",
  "ArrowDown",
  "ArrowRight",
  "ArrowUp",
];

export default function useCheatCode() {
  // Utiliser useRef pour éviter les re-rendus à chaque touche
  const sequenceRef = useRef([]);
  const [hasPrivateAccess, setHasPrivateAccess] = useLocalStorage(
    "hasPrivateAccess",
    false
  );

  // Mémoriser la fonction de vérification pour éviter de la recréer à chaque rendu
  const checkSequence = useCallback(() => {
    const currentSequence = sequenceRef.current;
    return currentSequence.join(",") === CHEAT_CODE.join(",");
  }, []);

  // Mémoriser la fonction handleKeyDown pour éviter les re-rendus inutiles
  const handleKeyDown = useCallback(
    (event) => {
      // Ajouter la nouvelle touche à la séquence
      const newSequence = [...sequenceRef.current, event.key];

      // Ne garder que les dernières touches correspondant à la longueur du cheat code
      if (newSequence.length > CHEAT_CODE.length) {
        newSequence.shift();
      }

      // Mettre à jour la séquence sans causer de re-rendu
      sequenceRef.current = newSequence;

      // Vérifier si la séquence correspond au cheat code
      if (checkSequence()) {
        setHasPrivateAccess(true);
        // Réinitialiser la séquence
        sequenceRef.current = [];
      }
    },
    [checkSequence, setHasPrivateAccess]
  );

  // N'ajouter l'event listener qu'une seule fois
  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Mémoriser la fonction pour désactiver l'accès privé
  const disablePrivateAccess = useCallback(() => {
    setHasPrivateAccess(false);
    sequenceRef.current = [];
  }, [setHasPrivateAccess]);

  return {
    hasPrivateAccess,
    disablePrivateAccess,
  };
}
