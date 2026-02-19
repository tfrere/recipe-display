import axios from "axios";

const API_URL = `${import.meta.env.VITE_API_ENDPOINT}/api`;
const PRIVATE_TOKEN = import.meta.env.VITE_PRIVATE_TOKEN || "";

function getPrivateHeaders() {
  const hasAccess = JSON.parse(localStorage.getItem("hasPrivateAccess") || "false");
  if (hasAccess && PRIVATE_TOKEN) {
    return { "X-Private-Token": PRIVATE_TOKEN };
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
    const headers = hasPrivateAccess ? { "X-Private-Token": PRIVATE_TOKEN } : {};
    const response = await axios.get(`${API_URL}/recipes`, { params, headers });
    return response.data;
  } catch (error) {
    console.error("Error fetching recipes:", error);
    throw error;
  }
};
