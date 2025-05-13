import { useState, useRef, useCallback, useEffect } from "react";
import useLocalStorage from "./useLocalStorage";

// Créer un bus d'événements simple pour la communication entre les composants
const eventBus = {
  listeners: {},
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    console.log(
      `[EventBus] Listener added for ${event}, total: ${this.listeners[event].length}`
    );
    // Retourner une fonction pour se désabonner
    return () => {
      this.listeners[event] = this.listeners[event].filter(
        (cb) => cb !== callback
      );
      console.log(
        `[EventBus] Listener removed for ${event}, remaining: ${this.listeners[event].length}`
      );
    };
  },
  emit(event, data) {
    console.log(`[EventBus] Emitting event: ${event}`, data);
    if (this.listeners[event]) {
      console.log(
        `[EventBus] Number of listeners: ${this.listeners[event].length}`
      );
      this.listeners[event].forEach((callback) => callback(data));
    } else {
      console.log(`[EventBus] No listeners for event: ${event}`);
    }
  },
};

// Exposer un événement pour le changement d'état d'accès privé
export const PRIVATE_ACCESS_CHANGED = "privateAccessChanged";

const LONG_PRESS_DURATION = 5000; // 5 secondes en millisecondes

export default function useLongPress() {
  const [hasPrivateAccess, setHasPrivateAccess] = useLocalStorage(
    "hasPrivateAccess",
    false
  );
  const timerRef = useRef(null);
  const [pressing, setPressing] = useState(false);

  // Fonction pour mettre à jour l'accès privé et émettre un événement
  const updatePrivateAccess = useCallback(
    (value) => {
      console.log(`[useLongPress] Updating private access to: ${value}`);
      setHasPrivateAccess(value);

      // Ajouter un court délai pour s'assurer que localStorage est bien mis à jour
      setTimeout(() => {
        eventBus.emit(PRIVATE_ACCESS_CHANGED, value);

        // Forcer un rechargement de la page dans tous les cas
        // C'est la solution la plus fiable pour s'assurer que tout est mis à jour
        console.log(
          `[useLongPress] Forcing page reload after changing admin status to: ${value}`
        );
        window.location.reload();
      }, 100);
    },
    [setHasPrivateAccess]
  );

  // Fonction pour commencer l'appui long
  const startPress = useCallback(() => {
    setPressing(true);
    timerRef.current = setTimeout(() => {
      updatePrivateAccess(true);
      setPressing(false);
    }, LONG_PRESS_DURATION);
  }, [updatePrivateAccess]);

  // Fonction pour annuler l'appui long
  const endPress = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setPressing(false);
  }, []);

  // Fonction pour désactiver l'accès privé
  const disablePrivateAccess = useCallback(() => {
    updatePrivateAccess(false);
  }, [updatePrivateAccess]);

  // Propriétés à passer au composant
  const longPressProps = {
    onMouseDown: startPress,
    onMouseUp: endPress,
    onMouseLeave: endPress,
    onTouchStart: startPress,
    onTouchEnd: endPress,
    onTouchCancel: endPress,
  };

  // Fonction pour s'abonner aux changements d'état d'accès privé
  const onPrivateAccessChange = useCallback((callback) => {
    return eventBus.on(PRIVATE_ACCESS_CHANGED, callback);
  }, []);

  return {
    hasPrivateAccess,
    disablePrivateAccess,
    pressing,
    longPressProps,
    onPrivateAccessChange,
  };
}
