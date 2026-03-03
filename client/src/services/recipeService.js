import axios from "axios";

const API_URL = `${import.meta.env.VITE_API_ENDPOINT}/api`;

function getPrivateToken() {
  try {
    return JSON.parse(localStorage.getItem("privateToken") || "null");
  } catch {
    return null;
  }
}

function getPrivateHeaders() {
  const hasAccess = JSON.parse(localStorage.getItem("hasPrivateAccess") || "false");
  const token = getPrivateToken();
  if (hasAccess && token) {
    return { "X-Private-Token": token };
  }
  return {};
}

export const getRecipe = async (slug) => {
  try {
    const response = await axios.get(`${API_URL}/recipes/${slug}`, {
      headers: getPrivateHeaders(),
    });
    return response.data;
  } catch (error) {
    console.error(`Error fetching recipe ${slug}:`, error);
    throw error;
  }
};

export const getRecipes = async (hasPrivateAccess = false) => {
  try {
    const params = hasPrivateAccess ? { include_private: true } : {};
    const headers = hasPrivateAccess ? getPrivateHeaders() : {};
    const response = await axios.get(`${API_URL}/recipes`, { params, headers });
    return response.data;
  } catch (error) {
    console.error("Error fetching recipes:", error);
    throw error;
  }
};
