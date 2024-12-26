import React, { useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { Box } from '@mui/material';
import { useRecipe } from '../../../contexts/RecipeContext';
import { CustomNode } from './nodes/CustomNode';
import { prepareGraphData } from './utils/graphUtils';
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
    ranker: "network-simplex"
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: node.data.type === "action" ? 250 : 120,
      height: node.data.type === "action" ? 250 : 60,
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

const GraphView = () => {
  const { recipe, completedSteps, toggleStepCompletion, calculateUnusedItems } = useRecipe();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  React.useEffect(() => {
    if (!recipe) {
      setNodes([]);
      setEdges([]);
      return;
    }

    dagreGraph.setGraph({});
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const { unusedIngredients, unusedTools, unusedStates } = calculateUnusedItems();
    
    let allNodes = [];
    let allLinks = [];
    
    Object.entries(recipe.subRecipes).forEach(([subRecipeId, subRecipe]) => {
      const subGraphData = prepareGraphData(subRecipe, recipe, subRecipeId);
      allNodes.push(...subGraphData.nodes);
      allLinks.push(...subGraphData.links);
    });

    const newNodes = allNodes.map((node) => {
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
        position: { x: 0, y: 0 },
        data: {
          ...node,
          isCompleted: completedSteps[node.id],
          isUnused,
          onToggleComplete: () => toggleStepCompletion(node.id),
        },
      };
    });

    const newEdges = allLinks.map((link, index) => ({
      id: `edge-${index}`,
      source: link.source,
      target: link.target,
      type: "smoothstep",
      animated: true,
    }));

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      newNodes,
      newEdges
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [recipe, completedSteps]);

  return (
    <Box sx={{ 
      height: '100%',
      width: '100%',
      position: 'relative'
    }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.01}
        maxZoom={4}
        proOptions={{ hideAttribution: true }}
      >
        <Controls />
        <Background />
        <MiniMap />
      </ReactFlow>
    </Box>
  );
};

export default GraphView;
