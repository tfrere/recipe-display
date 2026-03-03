import { useCallback } from "react";
import axios from "axios";
import useLocalStorage from "./useLocalStorage";

const API_URL = `${import.meta.env.VITE_API_ENDPOINT}/api`;

const eventBus = {
  listeners: {},
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    return () => {
      this.listeners[event] = this.listeners[event].filter(
        (cb) => cb !== callback
      );
    };
  },
  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((callback) => callback(data));
    }
  },
};

export const PRIVATE_ACCESS_CHANGED = "privateAccessChanged";

export default function useLongPress() {
  const [hasPrivateAccess, setHasPrivateAccess] = useLocalStorage(
    "hasPrivateAccess",
    false
  );

  const login = useCallback(
    async (password) => {
      const response = await axios.post(`${API_URL}/auth/login`, { password });
      const { token } = response.data;
      localStorage.setItem("privateToken", JSON.stringify(token));
      setHasPrivateAccess(true);
      eventBus.emit(PRIVATE_ACCESS_CHANGED, true);
    },
    [setHasPrivateAccess]
  );

  const disablePrivateAccess = useCallback(() => {
    localStorage.removeItem("privateToken");
    setHasPrivateAccess(false);
    eventBus.emit(PRIVATE_ACCESS_CHANGED, false);
  }, [setHasPrivateAccess]);

  const onPrivateAccessChange = useCallback((callback) => {
    return eventBus.on(PRIVATE_ACCESS_CHANGED, callback);
  }, []);

  return {
    hasPrivateAccess,
    login,
    disablePrivateAccess,
    onPrivateAccessChange,
  };
}
