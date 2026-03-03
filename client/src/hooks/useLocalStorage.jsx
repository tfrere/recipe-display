import { useState, useEffect, useCallback } from "react";

const EVENT_NAME = "local-storage-sync";

const useLocalStorage = (key, initialValue) => {
  const initialize = () => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  };

  const [storedValue, setStoredValue] = useState(initialize);

  const setValue = useCallback(
    (value) => {
      try {
        const valueToStore =
          value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        localStorage.setItem(key, JSON.stringify(valueToStore));
        window.dispatchEvent(
          new CustomEvent(EVENT_NAME, { detail: { key } })
        );
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, storedValue]
  );

  useEffect(() => {
    const onSync = (e) => {
      if (e.detail?.key === key) {
        try {
          const item = localStorage.getItem(key);
          if (item !== null) setStoredValue(JSON.parse(item));
        } catch (error) {
          console.warn(`Error syncing localStorage key "${key}":`, error);
        }
      }
    };

    const onStorageEvent = (e) => {
      if (e.key === key && e.newValue !== null) {
        try {
          setStoredValue(JSON.parse(e.newValue));
        } catch (error) {
          console.warn(`Error parsing cross-tab localStorage key "${key}":`, error);
        }
      }
    };

    window.addEventListener(EVENT_NAME, onSync);
    window.addEventListener("storage", onStorageEvent);
    return () => {
      window.removeEventListener(EVENT_NAME, onSync);
      window.removeEventListener("storage", onStorageEvent);
    };
  }, [key]);

  return [storedValue, setValue];
};

export default useLocalStorage;
