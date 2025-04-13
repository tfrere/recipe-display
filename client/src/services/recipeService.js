import axios from "axios";

const API_URL = `${import.meta.env.VITE_API_ENDPOINT}/api`;

export const getRecipes = async (hasPrivateAccess = false) => {
  try {
    const params = hasPrivateAccess ? { include_private: true } : {};
    const response = await axios.get(`${API_URL}/recipes`, { params });
    return response.data;
  } catch (error) {
    console.error("Error fetching recipes:", error);
    throw error;
  }
};
