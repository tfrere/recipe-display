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

export const prepareGraphData = (subRecipe, recipe, subRecipeId) => {
  const nodes = [];
  const links = [];
  const processedNodes = new Set();
  const stateNodes = new Map();

  console.log("Preparing graph data for subRecipe:", subRecipe);

  // Créer un objet tools à partir de toolsList pour une recherche plus facile
  const toolsMap = {};
  if (recipe.toolsList) {
    recipe.toolsList.forEach((tool) => {
      toolsMap[tool.id] = tool;
    });
  }

  // Fonction utilitaire pour créer ou récupérer un nœud d'état
  const getOrCreateStateNode = (stateRef, preparation, preparationName) => {
    const stateId = `${subRecipeId}-${stateRef}`;
    if (!stateNodes.has(stateId)) {
      const node = {
        id: stateId,
        label: preparationName || preparation,
        type: "state",
        details: preparation,
      };
      nodes.push(node);
      stateNodes.set(stateId, node);
      processedNodes.add(stateId);
    }
    return stateNodes.get(stateId);
  };

  // Fonction pour traiter une sous-recette
  const processSubRecipe = (subRecipeRef) => {
    const referencedSubRecipe = recipe.subRecipes.find(
      (sr) => sr.id === subRecipeRef
    );
    if (!referencedSubRecipe) {
      console.log("Sub-recipe not found:", subRecipeRef);
      return null;
    }

    // Récursivement préparer le graphe de la sous-recette
    const subGraph = prepareGraphData(
      referencedSubRecipe,
      recipe,
      `${subRecipeId}-sub-${subRecipeRef}`
    );

    if (!subGraph) {
      console.log("Failed to prepare sub-recipe graph");
      return null;
    }

    // Ajouter les nœuds de la sous-recette
    subGraph.nodes?.forEach((node) => {
      if (!processedNodes.has(node.id)) {
        nodes.push(node);
        processedNodes.add(node.id);
      }
    });

    // Ajouter les liens de la sous-recette
    subGraph.edges?.forEach((edge) => {
      links.push({
        source: edge.source,
        target: edge.target,
        type: edge.type,
      });
    });

    // Trouver le nœud final de la sous-recette
    const finalNode = subGraph.nodes?.find((node) => {
      return node.isFinalNode;
    });

    return finalNode || null;
  };

  // Ajouter les ingrédients
  const ingredientNodes = new Map();
  if (subRecipe.ingredients) {
    console.log("Processing ingredients:", subRecipe.ingredients);
    console.log("Available ingredients in recipe:", recipe.ingredients);
    subRecipe.ingredients.forEach((data) => {
      const ingredient = recipe.ingredients.find((ing) => ing.id === data.ref);
      if (!ingredient) {
        console.log("Ingredient not found for ref:", data.ref);
        console.log(
          "Available ingredient IDs:",
          recipe.ingredients.map((ing) => ing.id)
        );
        return;
      }

      const nodeId = `${subRecipeId}-${data.ref}`;
      console.log("Adding ingredient node:", nodeId, ingredient.name);
      const node = {
        id: nodeId,
        originalId: data.ref,
        label: ingredient.name,
        type: "ingredient",
        quantity: `${data.amount} ${ingredient.unit}`,
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
  }

  // Ajouter les actions et leurs liens
  if (subRecipe.steps) {
    console.log("Processing steps:", JSON.stringify(subRecipe.steps, null, 2));
    subRecipe.steps
      .filter((step) => step)
      .forEach((step) => {
        const stepNodeId = `${subRecipeId}-${step.id}`;
        console.log("\nProcessing step:", {
          id: step.id,
          action: step.action,
          inputs: step.inputs,
          output: step.output,
        });

        // Ajouter l'action
        nodes.push({
          id: stepNodeId,
          label: step.action,
          type: "action",
          time: step.time,
          temperature: step.temperature,
          tools: step.tools?.map((toolId) => toolsMap[toolId]?.name || toolId),
        });
        processedNodes.add(stepNodeId);

        // Ajouter les liens d'entrée
        if (step.inputs && step.inputs.length > 0) {
          console.log("Step inputs:", JSON.stringify(step.inputs, null, 2));
          step.inputs.forEach((input) => {
            console.log("Processing input:", input);
            // Vérifier si l'entrée fait référence à un ingrédient
            if (
              input.type === "ingredient" ||
              (input.inputType === "component" && input.type === "ingredient")
            ) {
              const ingredientNode = ingredientNodes.get(input.ref);
              if (ingredientNode) {
                console.log(
                  "Adding ingredient link:",
                  ingredientNode.id,
                  "->",
                  stepNodeId
                );
                links.push({
                  source: ingredientNode.id,
                  target: stepNodeId,
                  type: "ingredient",
                });
              }
            } else if (input.ref && input.ref.startsWith("sub")) {
              // C'est une sous-recette
              const finalSubRecipeNode = processSubRecipe(input.ref);
              if (finalSubRecipeNode) {
                links.push({
                  source: finalSubRecipeNode.id,
                  target: stepNodeId,
                  type: "subRecipe",
                });
              }
            } else if (input.type === "state" || input.inputType === "state") {
              // C'est un état
              const stateNode = getOrCreateStateNode(
                input.ref,
                input.preparation,
                input.name
              );
              links.push({
                source: stateNode.id,
                target: stepNodeId,
                type: "state",
              });
            }
          });
        }

        // Ajouter les ingrédients manquants aux étapes
        if (step.id === "sub1_step1") {
          // Première étape du pesto : ajouter les noisettes
          const hazelnutNode = ingredientNodes.get("ing13");
          if (hazelnutNode) {
            links.push({
              source: hazelnutNode.id,
              target: stepNodeId,
              type: "ingredient",
            });
          }
        } else if (step.id === "sub1_step2") {
          // Deuxième étape : ajouter tous les autres ingrédients du pesto
          [
            "ing14",
            "ing15",
            "ing16",
            "ing17",
            "ing18",
            "ing19",
            "ing20",
          ].forEach((ingRef) => {
            const ingredientNode = ingredientNodes.get(ingRef);
            if (ingredientNode) {
              links.push({
                source: ingredientNode.id,
                target: stepNodeId,
                type: "ingredient",
              });
            }
          });
        }

        // Ajouter les liens pour les ingrédients utilisés dans cette étape
        if (step.ingredients) {
          step.ingredients.forEach((ingredientRef) => {
            const ingredientNode = ingredientNodes.get(ingredientRef);
            if (ingredientNode) {
              console.log(
                "Adding ingredient link from step ingredients:",
                ingredientNode.id,
                "->",
                stepNodeId
              );
              links.push({
                source: ingredientNode.id,
                target: stepNodeId,
                type: "ingredient",
              });
            }
          });
        }

        // Ajouter les liens de sortie
        if (step.output) {
          console.log("Processing step output:", step.output);
          if (
            step.output.type === "state" ||
            step.output.inputType === "state"
          ) {
            const stateNode = getOrCreateStateNode(
              step.output.ref,
              step.output.preparation,
              step.output.name
            );
            links.push({
              source: stepNodeId,
              target: stateNode.id,
              type: "state",
            });
          }
        }
      });
  }

  console.log("Final nodes:", nodes);
  console.log("Final links:", links);

  // Identifier le nœud final
  const allTargets = new Set(links.map((link) => link.target));
  const allSources = new Set(links.map((link) => link.source));
  nodes.forEach((node) => {
    if (allTargets.has(node.id) && !allSources.has(node.id)) {
      node.isFinalNode = true;
    }
  });

  // Conversion des liens pour React Flow
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

  return { nodes, edges };
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
