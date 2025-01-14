import axios from "axios";

const API_URL = `${import.meta.env.VITE_API_ENDPOINT}/api`;

export const getAuthors = async (includePrivate = false) => {
  try {
    const response = await axios.get(`${API_URL}/authors`, {
      params: { include_private: includePrivate },
    });
    return response.data;
  } catch (error) {
    console.error("Error fetching authors:", error);
    throw error;
  }
};
