import React from "react";
import ReactFlow, {
  Background,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import { Box, useTheme } from "@mui/material";
import { useRecipe } from "../../../contexts/RecipeContext";
import { CustomNode } from "./nodes/CustomNode";
import { prepareGraphData, calculateNodeHeight } from "./utils/graphUtils";
import dagre from "dagre";

const nodeTypes = {
  custom: CustomNode,
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

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
      height: node.data.height,
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

export const GraphContent = () => {
  const { recipe } = useRecipe();
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
    Object.entries(recipe.subRecipes || {}).forEach(
      ([subRecipeId, subRecipe]) => {
        const { nodes: subNodes, edges: subEdges } = prepareGraphData(
          subRecipe,
          recipe,
          subRecipeId
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
      }
    );

    // Créer les nœuds React Flow
    const rfNodes = allNodes.map((node) => ({
      id: node.id,
      type: "custom",
      position: { x: 0, y: 0 }, // Position temporaire
      data: {
        ...node,
        label: node.label,
        type: node.type,
        time: node.time,
        tools: node.tools,
        quantity: node.quantity,
        state: node.state,
        details: node.details,
        isCompleted: false,
        height: node.data?.height,
      },
    }));

    // Obtenir la disposition avec dagre
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      rfNodes,
      allEdges
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [recipe, setNodes, setEdges]);

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        position: "relative",
        bgcolor: "background.default",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        style={{ background: "transparent" }}
        minZoom={0.1}
        maxZoom={4}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={true}
        zoomOnScroll={true}
        defaultEdgeOptions={{
          type: "bezier",
          animated: true,
        }}
      >
        <Background color="#999" gap={16} />
      </ReactFlow>
    </Box>
  );
};

import GraphModal from "./GraphModal";

const GraphView = () => (
  <ReactFlowProvider>
    <GraphModal>
      <GraphContent />
    </GraphModal>
  </ReactFlowProvider>
);

export default GraphView;
