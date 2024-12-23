import React, { useMemo, useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { Box } from "@mui/material";
import dagre from "dagre";
import { useRecipe } from "../../contexts/RecipeContext";
import { CustomNode } from "./nodes/CustomNode";
import { prepareGraphData } from "./utils/graphUtils";

// Définition des types de nœuds personnalisés
const nodeTypes = {
  custom: CustomNode,
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

// Configuration du layout
const getLayoutedElements = (nodes, edges, direction = "LR") => {
  const isHorizontal = direction === "LR";
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 50,
    ranksep: 100,
    edgesep: 25,
    marginx: 50,
    marginy: 50,
  });

  // Ajouter les nœuds au graphe dagre avec des dimensions fixes
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: node.data.type === "action" ? 250 : 160,
      height: node.data.type === "action" ? 250 : 160,
    });
  });

  // Ajouter les liens au graphe dagre
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Calculer le layout
  dagre.layout(dagreGraph);

  // Récupérer les positions calculées
  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - (node.data.type === "action" ? 125 : 80),
      y: nodeWithPosition.y - (node.data.type === "action" ? 125 : 80),
    };
  });

  // Convertir les liens en courbes
  const edgesWithBezier = edges.map((edge) => ({
    ...edge,
    type: "smoothstep",
    animated: false,
    style: {
      ...edge.style,
      strokeWidth: 2,
      radius: 20,
    },
    markerEnd: {
      type: "arrowclosed",
      width: 20,
      height: 20,
      color: edge.style.stroke,
    },
  }));

  return { nodes, edges: edgesWithBezier };
};

const GraphView = () => {
  const {
    recipe,
    selectedSubRecipe,
    completedSteps,
    toggleStepCompletion,
    calculateUnusedItems,
  } = useRecipe();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Effet pour reconstruire complètement le graphe quand la sous-recette change
  useEffect(() => {
    if (
      !recipe ||
      !selectedSubRecipe ||
      !recipe.subRecipes[selectedSubRecipe]
    ) {
      setNodes([]);
      setEdges([]);
      return;
    }

    // Nettoyer le graphe dagre
    dagreGraph.setGraph({});
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const { unusedIngredients, unusedTools, unusedStates } =
      calculateUnusedItems();
    const graphData = prepareGraphData(
      recipe.subRecipes[selectedSubRecipe],
      recipe,
      selectedSubRecipe
    );

    // Conversion des nœuds pour React Flow
    const newNodes = graphData.nodes.map((node) => {
      let isUnused = false;
      if (node.type === "ingredient") {
        isUnused = unusedIngredients[node.originalId];
      } else if (node.type === "tool") {
        isUnused = unusedTools[node.originalId];
      } else if (node.type === "state") {
        isUnused = unusedStates.has(node.id);
      }

      return {
        id: node.id,
        type: "custom",
        draggable: true,
        selectable: false,
        position: { x: 0, y: 0 },
        data: {
          ...node,
          isUnused,
          isCompleted: completedSteps[node.id],
          onClick:
            node.type === "action"
              ? () =>
                  toggleStepCompletion(
                    node.id,
                    !completedSteps[node.id],
                    selectedSubRecipe
                  )
              : undefined,
        },
      };
    });

    // Conversion des liens pour React Flow
    const newEdges = graphData.links.map((link, index) => ({
      id: `edge-${index}`,
      source: link.source.id || link.source,
      target: link.target.id || link.target,
      type: "smoothstep",
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

    // Appliquer le layout
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      newNodes,
      newEdges,
      "LR"
    );

    // Mettre à jour l'état avec les nouveaux nœuds et liens
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [
    recipe,
    selectedSubRecipe,
    completedSteps,
    toggleStepCompletion,
    calculateUnusedItems,
  ]);

  // Effet pour mettre à jour l'état des nœuds quand completedSteps change
  useEffect(() => {
    if (nodes.length === 0) return;

    const { unusedIngredients, unusedTools, unusedStates } =
      calculateUnusedItems();

    setNodes((nds) =>
      nds.map((node) => {
        let isUnused = false;
        if (node.data.type === "ingredient") {
          isUnused = unusedIngredients[node.data.originalId];
        } else if (node.data.type === "tool") {
          isUnused = unusedTools[node.data.originalId];
        } else if (node.data.type === "state") {
          isUnused = unusedStates.has(node.id);
        }

        return {
          ...node,
          data: {
            ...node.data,
            isUnused,
            isCompleted: completedSteps[node.id],
            onClick:
              node.data.type === "action"
                ? () =>
                    toggleStepCompletion(
                      node.id,
                      !completedSteps[node.id],
                      selectedSubRecipe
                    )
                : undefined,
          },
        };
      })
    );
  }, [completedSteps, calculateUnusedItems]);

  const defaultEdgeOptions = {
    type: "smoothstep",
    style: {
      strokeWidth: 2,
      radius: 20,
    },
    markerEnd: {
      type: "arrowclosed",
      width: 20,
      height: 20,
    },
    animated: false,
  };

  return (
    <Box sx={{ width: "100%", height: "100%", position: "relative" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3, duration: 200 }}
        defaultEdgeOptions={defaultEdgeOptions}
        minZoom={0.1}
        maxZoom={1.5}
        attributionPosition="bottom-left"
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
      >
        <Background gap={20} size={1} />
        <Controls showInteractive={true} />
        <MiniMap
          nodeColor={(node) => {
            switch (node.data.type) {
              case "action":
                return "#fff3e0";
              case "ingredient":
                return "#e3f2fd";
              case "state":
                return "#f3e5f5";
              default:
                return "#fff";
            }
          }}
          maskColor="rgba(255, 255, 255, 0.8)"
        />
      </ReactFlow>
    </Box>
  );
};

export default GraphView;
