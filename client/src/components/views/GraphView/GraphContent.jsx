import React from "react";
import ReactFlow, {
  Background,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";
import { Box } from "@mui/material";
import { useRecipe } from "../../../contexts/RecipeContext";
import { CustomNode } from "./nodes/CustomNode";
import { prepareGraphData } from "./utils/graphUtils";
import dagre from "dagre";

const nodeTypes = {
  custom: CustomNode,
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const calculateNodeHeight = (node) => {
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

const getLayoutedElements = (nodes, edges) => {
  dagreGraph.setGraph({
    rankdir: "LR",
    align: "UL",
    nodesep: 30,
    ranksep: 150,
    edgesep: 20,
    marginx: 50,
    marginy: 50,
    acyclicer: "greedy",
    ranker: "network-simplex",
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: node.data.type === "action" ? 250 : 120,
      height: node.data.height || 60,
    });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWithPosition.width / 2,
        y: nodeWithPosition.y - nodeWithPosition.height / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

const GraphContent = () => {
  const { recipe, completedSteps } = useRecipe();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { updateNodeInternals } = useReactFlow();

  React.useEffect(() => {
    if (!recipe) {
      setNodes([]);
      setEdges([]);
      return;
    }

    dagreGraph.setGraph({});
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    let allNodes = [];
    let allEdges = [];

    // Traiter chaque sous-recette
    const subRecipes = Array.isArray(recipe.subRecipes)
      ? recipe.subRecipes
      : Object.values(recipe.subRecipes || {});

    subRecipes.forEach((subRecipe) => {
      const { nodes: subNodes, edges: subEdges } = prepareGraphData(
        subRecipe,
        recipe,
        subRecipe.id
      );

      // Ajouter la hauteur calculée à chaque nœud d'action
      const nodesWithHeight = subNodes.map((node) => {
        if (node.type === "action") {
          return {
            ...node,
            data: {
              ...node.data,
              height: calculateNodeHeight(node),
            },
          };
        }
        return node;
      });

      allNodes = [...allNodes, ...nodesWithHeight];
      allEdges = [...allEdges, ...subEdges];
    });

    // Créer les nœuds React Flow
    const rfNodes = allNodes.map((node) => ({
      id: node.id,
      type: "custom",
      position: { x: 0, y: 0 }, // Position temporaire
      data: {
        label: node.label,
        type: node.type,
        time: node.time,
        tools: node.tools,
        quantity: node.quantity,
        isCompleted: completedSteps[node.id] || false,
        height: node.data?.height || 60,
      },
    }));

    // Obtenir la disposition avec dagre
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      rfNodes,
      allEdges
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [recipe, completedSteps, setNodes, setEdges]);

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        position: "relative",
        bgcolor: "background.default",
        minHeight: "500px", // Hauteur minimale
        display: "flex",
        flexDirection: "column",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        style={{ background: "transparent", flex: 1 }}
        minZoom={0.1}
        maxZoom={4}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={true}
        zoomOnScroll={true}
        defaultEdgeOptions={{
          type: "smoothstep",
          animated: false,
        }}
      >
        <Background variant="dots" gap={20} size={1} color="#00000010" />
      </ReactFlow>
    </Box>
  );
};

export default GraphContent;
