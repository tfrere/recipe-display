import { useEffect, useState } from "react";
import useLocalStorage from "./useLocalStorage";

// Définition du cheat code : gauche, bas, droite, haut
const CHEAT_CODE = ["ArrowLeft", "ArrowDown", "ArrowRight", "ArrowUp"];

export default function useCheatCode() {
  const [sequence, setSequence] = useState([]);
  const [hasPrivateAccess, setHasPrivateAccess] = useLocalStorage(
    "hasPrivateAccess",
    false
  );

  useEffect(() => {
    const handleKeyDown = (event) => {
      // Ajouter la nouvelle touche à la séquence
      const newSequence = [...sequence, event.key];

      // Ne garder que les dernières touches correspondant à la longueur du cheat code
      if (newSequence.length > CHEAT_CODE.length) {
        newSequence.shift();
      }

      setSequence(newSequence);

      // Vérifier si la séquence correspond au cheat code
      if (newSequence.join(",") === CHEAT_CODE.join(",")) {
        setHasPrivateAccess(true);
        // Réinitialiser la séquence
        setSequence([]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [sequence, setHasPrivateAccess]);

  // Fonction pour désactiver l'accès privé
  const disablePrivateAccess = () => {
    setHasPrivateAccess(false);
    setSequence([]);
  };

  return {
    hasPrivateAccess,
    disablePrivateAccess,
  };
}
