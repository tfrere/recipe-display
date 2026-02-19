// Calcule la hauteur d'un nœud en fonction de son contenu
export const calculateNodeHeight = (node) => {
  if (node.type !== "action") return 60;

  // Estimation de la hauteur basée sur le contenu
  let height = 100; // Hauteur de base réduite

  // Ajouter de l'espace pour le label (environ 24px par ligne)
  const estimatedLines = Math.ceil(node.label.length / 30); // ~30 caractères par ligne
  height += (estimatedLines - 1) * 24;

  // Ajouter de l'espace pour le temps
  if (node.time) height += 30;

  // Ajouter de l'espace pour les outils
  if (node.tools?.length) {
    height += Math.ceil(node.tools.length / 2) * 28; // ~2 outils par ligne
  }

  return height;
};

/**
 * Build graph data for a single sub-recipe.
 * Each sub-recipe gets its own isolated graph.
 */
export const prepareGraphData = (subRecipe, recipe, subRecipeId) => {
  return prepareGraphDataUnified([subRecipe], recipe, subRecipeId);
};

/**
 * Build a unified graph across all sub-recipes.
 * States produced in one sub-recipe are properly linked when consumed in another.
 * This avoids duplicate state nodes and disconnected graphs.
 */
export const prepareGraphDataUnified = (subRecipes, recipe, graphId = "graph") => {
  const nodes = [];
  const links = [];
  const processedNodes = new Set();
  const stateNodes = new Map(); // Global across all sub-recipes
  const ingredientNodes = new Map(); // Global across all sub-recipes

  // Build tools map (recipe.tools is an array of tool name strings)
  const toolsMap = {};
  if (Array.isArray(recipe.tools)) {
    recipe.tools.forEach((tool) => {
      if (typeof tool === "object" && tool.id) {
        toolsMap[tool.id] = tool;
      } else if (typeof tool === "string") {
        toolsMap[tool] = { id: tool, name: tool };
      }
    });
  }

  // Build ingredients map for quick lookup
  const ingredientsMap = {};
  (recipe.ingredients || []).forEach((ing) => {
    ingredientsMap[ing.id] = ing;
  });

  // Global function to create or retrieve a state node (shared across sub-recipes)
  const getOrCreateStateNode = (stateRef, label) => {
    const stateId = `state-${stateRef}`;
    if (!stateNodes.has(stateId)) {
      const node = {
        id: stateId,
        label: label || stateRef.replace(/_/g, " "),
        type: "state",
        details: stateRef,
      };
      nodes.push(node);
      stateNodes.set(stateId, node);
      processedNodes.add(stateId);
    }
    return stateNodes.get(stateId);
  };

  // First pass: add all ingredient nodes (deduplicated across sub-recipes)
  subRecipes.forEach((subRecipe) => {
    if (!subRecipe.ingredients) return;

    subRecipe.ingredients.forEach((data) => {
      if (ingredientNodes.has(data.ref)) return; // Already added

      const ingredient = recipe.ingredients.find((ing) => ing.id === data.ref);
      if (!ingredient) return;

      const nodeId = `ing-${data.ref}`;
      const node = {
        id: nodeId,
        originalId: data.ref,
        label: ingredient.name,
        type: "ingredient",
        quantity: data.amount != null ? `${data.amount} ${ingredient.unit || ""}`.trim() : "",
        state: data.state,
        details: data.state
          ? `${ingredient.name}\n${data.state}`
          : ingredient.name,
        style: {
          background: "#f5f5f5",
          border: "1px solid #e0e0e0",
          borderRadius: "4px",
          padding: "8px",
          fontSize: "12px",
          fontFamily: "system-ui",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "4px",
        },
      };
      nodes.push(node);
      ingredientNodes.set(data.ref, node);
      processedNodes.add(nodeId);
    });
  });

  // Second pass: add all step nodes and links
  subRecipes.forEach((subRecipe) => {
    if (!subRecipe.steps) return;

    subRecipe.steps
      .filter((step) => step)
      .forEach((step) => {
        const stepNodeId = `step-${step.id}`;

        // Determine tools to display
        const stepTools = (step.requires || step.tools || []).map(
          (toolId) => toolsMap[toolId]?.name || toolId
        );

        // Add action node
        nodes.push({
          id: stepNodeId,
          label: step.action,
          type: "action",
          time: step.time,
          temperature: step.temperature,
          tools: stepTools,
        });
        processedNodes.add(stepNodeId);

        // uses[] contains both ingredient refs and state refs
        if (step.uses) {
          step.uses.forEach((ref) => {
            const ingredientNode = ingredientNodes.get(ref);
            if (ingredientNode) {
              links.push({
                source: ingredientNode.id,
                target: stepNodeId,
                type: "ingredient",
              });
            } else {
              // It's a state produced by a previous step (possibly in another sub-recipe)
              const stateNode = getOrCreateStateNode(ref);
              links.push({
                source: stateNode.id,
                target: stepNodeId,
                type: "state",
              });
            }
          });
        }

        // produces is the output state
        if (step.produces) {
          const stateNode = getOrCreateStateNode(step.produces);
          links.push({
            source: stepNodeId,
            target: stateNode.id,
            type: "state",
          });
        }
      });
  });

  // Identify final node(s)
  const allTargets = new Set(links.map((link) => link.target));
  const allSources = new Set(links.map((link) => link.source));
  nodes.forEach((node) => {
    if (allTargets.has(node.id) && !allSources.has(node.id)) {
      node.isFinalNode = true;
    }
  });

  // Convert links to React Flow edges
  const edges = links.map((link) => ({
    id: `edge-${link.source}-${link.target}`,
    source: link.source,
    target: link.target,
    type: "smoothstep",
    style: {
      stroke:
        link.type === "ingredient"
          ? "#5c6bc0"
          : link.type === "state"
          ? "#9c27b0"
          : link.type === "subRecipe"
          ? "#ff8f00"
          : "#9c27b0",
      strokeWidth: 2,
    },
    markerEnd: {
      type: "arrowclosed",
      width: 20,
      height: 20,
      color:
        link.type === "ingredient"
          ? "#5c6bc0"
          : link.type === "state"
          ? "#9c27b0"
          : link.type === "subRecipe"
          ? "#ff8f00"
          : "#9c27b0",
    },
    animated: false,
  }));

  // Build sub-recipe membership map for compound nodes
  // Maps node ID → subRecipe name
  const nodeSubRecipeMap = {};
  subRecipes.forEach((subRecipe) => {
    const subRecipeName = subRecipe.title || subRecipe.id || "main";
    if (subRecipe.steps) {
      subRecipe.steps.filter(Boolean).forEach((step) => {
        nodeSubRecipeMap[`step-${step.id}`] = subRecipeName;
        // Also map the state this step produces
        if (step.produces) {
          nodeSubRecipeMap[`state-${step.produces}`] = subRecipeName;
        }
      });
    }
    // Map ingredients to a special "ingredients" group
    if (subRecipe.ingredients) {
      subRecipe.ingredients.forEach((data) => {
        nodeSubRecipeMap[`ing-${data.ref}`] = "__ingredients__";
      });
    }
  });

  return { nodes, edges, nodeSubRecipeMap };
};
