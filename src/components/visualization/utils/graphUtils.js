export const prepareGraphData = (subRecipe, recipe, subRecipeId) => {
  const nodes = [];
  const links = [];
  const processedNodes = new Set();

  // Ajouter les ingrédients
  if (subRecipe.ingredients) {
    Object.entries(subRecipe.ingredients).forEach(([ingredientId, data]) => {
      const nodeId = `${subRecipeId}-${ingredientId}`;
      nodes.push({
        id: nodeId,
        originalId: ingredientId,
        label: recipe.ingredients[ingredientId].name,
        type: "ingredient",
        quantity: `${data.amount} ${recipe.ingredients[ingredientId].unit}`,
      });
      processedNodes.add(nodeId);
    });
  }

  // Ajouter les actions et leurs liens
  subRecipe.steps.forEach((step) => {
    // Ajouter l'action
    nodes.push({
      id: step.id,
      label: step.action,
      type: "action",
      time: step.time,
      temperature: step.temperature,
      tools: step.tools?.map((toolId) => recipe.tools[toolId].name),
    });
    processedNodes.add(step.id);

    // Ajouter les liens d'entrée
    step.inputs.forEach((input) => {
      const sourceId =
        input.type === "ingredient" ? `${subRecipeId}-${input.ref}` : input.ref;

      links.push({
        source: sourceId,
        target: step.id,
        type: input.type,
      });
    });

    // Ajouter les liens de sortie
    if (step.output) {
      const stateId = step.output.state;
      nodes.push({
        id: stateId,
        label: step.output.description,
        type: "state",
      });
      processedNodes.add(stateId);

      links.push({
        source: step.id,
        target: stateId,
        type: "state",
      });
    }
  });

  // Identifier le nœud final
  const allTargets = new Set(links.map((link) => link.target));
  const allSources = new Set(links.map((link) => link.source));
  nodes.forEach((node) => {
    if (allTargets.has(node.id) && !allSources.has(node.id)) {
      node.isFinalNode = true;
    }
  });

  // Conversion des liens pour React Flow
  const edges = links.map((link, index) => ({
    id: `edge-${index}`,
    source: link.source,
    target: link.target,
    type: "bezier",
    style: {
      stroke:
        link.type === "ingredient"
          ? "#90caf9"
          : link.type === "state"
          ? "#ce93d8"
          : link.type === "subRecipe"
          ? "#ffd54f"
          : "#ce93d8",
      strokeWidth: 2,
    },
    markerEnd: {
      type: "arrowclosed",
      width: 20,
      height: 20,
      color:
        link.type === "ingredient"
          ? "#90caf9"
          : link.type === "state"
          ? "#ce93d8"
          : link.type === "subRecipe"
          ? "#ffd54f"
          : "#ce93d8",
    },
    animated: false,
  }));

  return { nodes, links };
};

const getEdgeType = (nodeId, subRecipe) => {
  // Vérifier si le nodeId correspond à un ingrédient
  const isIngredient = subRecipe.ingredients.some((ing) => ing.id === nodeId);
  if (isIngredient) return "ingredient";

  // Vérifier si le nodeId correspond à une sous-recette
  const isSubRecipe =
    subRecipe.subRecipes &&
    subRecipe.subRecipes.some((sub) => sub.id === nodeId);
  if (isSubRecipe) return "subRecipe";

  // Par défaut, c'est un état
  return "state";
};