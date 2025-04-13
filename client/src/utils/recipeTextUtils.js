import { getFormattedSubRecipes } from "./recipeStructureUtils";

/**
 * Formate une recette en texte pour l'impression ou la copie
 */
export const formatRecipeText = (recipe) => {
  console.log("Recipe in formatRecipeText:", recipe);
  const { metadata = {} } = recipe || {};
  const subRecipes = getFormattedSubRecipes(recipe);
  console.log("Formatted subRecipes:", subRecipes);

  let text = `${metadata.title}

${metadata.description || ""}

Pour ${metadata.servings} personnes${
    metadata.difficulty ? ` • ${metadata.difficulty}` : ""
  }${metadata.totalTime ? ` • ${metadata.totalTime}` : ""}

`;

  // Ajouter les ingrédients de chaque sous-recette
  text += "Ingrédients :\n";
  subRecipes.forEach((subRecipe) => {
    if (subRecipes.length > 1 && subRecipe.title) {
      text += `\n${subRecipe.title} :\n`;
    }
    text += subRecipe.ingredients.join("\n") + "\n";
  });

  // Ajouter les étapes de chaque sous-recette
  text += "\nPréparation :\n";
  subRecipes.forEach((subRecipe) => {
    if (subRecipes.length > 1 && subRecipe.title) {
      text += `\n${subRecipe.title} :\n`;
    }
    text += subRecipe.steps.join("\n") + "\n";
  });

  return text;
};

/**
 * Copie le texte de la recette dans le presse-papier
 */
export const copyRecipeToClipboard = (recipe) => {
  const recipeText = formatRecipeText(recipe);
  return navigator.clipboard.writeText(recipeText);
};

/**
 * Ouvre une fenêtre d'impression pour la recette
 */
export const printRecipe = (recipe) => {
  const recipeText = formatRecipeText(recipe);

  const printWindow = window.open("", "_blank");
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>${recipe.metadata.title}</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 2em auto;
            padding: 0 1em;
          }
          h1 {
            margin-bottom: 0.5em;
          }
          p {
            margin: 1em 0;
          }
          @media print {
            body {
              max-width: 100%;
              margin: 0;
              padding: 1em;
            }
          }
        </style>
      </head>
      <body>
        <pre style="white-space: pre-wrap; font-family: inherit;">${recipeText}</pre>
      </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.print();
  printWindow.close();
};
