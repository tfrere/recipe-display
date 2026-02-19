import React, { useCallback } from "react";
import ReactFlow, {
  Background,
  useNodesState,
  useEdgesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { Box } from "@mui/material";
import ELK from "elkjs/lib/elk.bundled.js";
import { useRecipe } from "../../../contexts/RecipeContext";
import { CustomNode } from "./nodes/CustomNode";
import { prepareGraphDataUnified, calculateNodeHeight } from "./utils/graphUtils";

const nodeTypes = {
  custom: CustomNode,
};

// ELK instance (reused across renders)
const elk = new ELK();

/**
 * Build the ELK graph structure from React Flow nodes/edges.
 *
 * We group nodes into compound "sub-recipe" children so that
 * ELK can route edges between groups cleanly.
 */
const buildElkGraph = (rfNodes, rfEdges, nodeSubRecipeMap) => {
  // Collect unique sub-recipe group names
  const groups = new Map(); // groupName → [nodeIds]
  const ungrouped = [];

  rfNodes.forEach((node) => {
    const group = nodeSubRecipeMap[node.id];
    if (group && group !== "__ingredients__") {
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(node);
    } else {
      ungrouped.push(node);
    }
  });

  // Build ELK children: either grouped in compound nodes or at root level
  const elkChildren = [];

  // Ingredient nodes go at the top level (no group)
  ungrouped.forEach((node) => {
    elkChildren.push({
      id: node.id,
      width: node.data.type === "action" ? 250 : 130,
      height: node.data.height || 60,
    });
  });

  // Sub-recipe groups as compound nodes
  groups.forEach((groupNodes, groupName) => {
    elkChildren.push({
      id: `group-${groupName}`,
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": "DOWN",
        "elk.layered.spacing.nodeNodeBetweenLayers": "80",
        "elk.spacing.nodeNode": "40",
        "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
        "elk.padding": "[top=40,left=20,bottom=20,right=20]",
      },
      children: groupNodes.map((node) => ({
        id: node.id,
        width: node.data.type === "action" ? 250 : 130,
        height: node.data.height || 60,
      })),
      edges: rfEdges
        .filter((e) => {
          const sourceInGroup = groupNodes.some((n) => n.id === e.source);
          const targetInGroup = groupNodes.some((n) => n.id === e.target);
          return sourceInGroup && targetInGroup;
        })
        .map((e) => ({
          id: e.id,
          sources: [e.source],
          targets: [e.target],
        })),
    });
  });

  // Top-level edges: edges that cross group boundaries or connect ungrouped nodes
  const groupNodeIds = new Set();
  groups.forEach((groupNodes) => {
    groupNodes.forEach((n) => groupNodeIds.add(n.id));
  });

  // For cross-group edges, ELK needs them at the root level
  // with sources/targets referencing the compound node path
  const topLevelEdges = rfEdges
    .filter((e) => {
      const sourceGroup = nodeSubRecipeMap[e.source];
      const targetGroup = nodeSubRecipeMap[e.target];
      // Edge is top-level if it crosses groups or involves ungrouped nodes
      return (
        !sourceGroup ||
        !targetGroup ||
        sourceGroup === "__ingredients__" ||
        targetGroup === "__ingredients__" ||
        sourceGroup !== targetGroup
      );
    })
    .map((e) => ({
      id: e.id,
      sources: [e.source],
      targets: [e.target],
    }));

  return {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "DOWN",
      "elk.layered.spacing.nodeNodeBetweenLayers": "100",
      "elk.spacing.nodeNode": "50",
      "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
      "elk.spacing.componentComponent": "60",
      "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
      "elk.hierarchyHandling": "INCLUDE_CHILDREN",
      "elk.padding": "[top=20,left=20,bottom=20,right=20]",
    },
    children: elkChildren,
    edges: topLevelEdges,
  };
};

/**
 * Flatten the ELK layout result back into React Flow node positions.
 * Compound children have positions relative to their parent,
 * so we need to add the parent offset.
 */
const flattenElkLayout = (elkResult) => {
  const positions = {}; // nodeId → { x, y }
  const groupBounds = {}; // groupId → { x, y, width, height }

  elkResult.children.forEach((child) => {
    if (child.children) {
      // This is a compound/group node
      const groupX = child.x || 0;
      const groupY = child.y || 0;
      groupBounds[child.id] = {
        x: groupX,
        y: groupY,
        width: child.width,
        height: child.height,
      };
      child.children.forEach((inner) => {
        positions[inner.id] = {
          x: groupX + (inner.x || 0),
          y: groupY + (inner.y || 0),
        };
      });
    } else {
      // Flat node
      positions[child.id] = {
        x: child.x || 0,
        y: child.y || 0,
      };
    }
  });

  return { positions, groupBounds };
};

const GraphContent = () => {
  const { recipe, completedSteps } = useRecipe();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const layoutGraph = useCallback(async (rfNodes, rfEdges, nodeSubRecipeMap) => {
    const elkGraph = buildElkGraph(rfNodes, rfEdges, nodeSubRecipeMap);

    try {
      const elkResult = await elk.layout(elkGraph);
      const { positions, groupBounds } = flattenElkLayout(elkResult);

      // Apply positions to React Flow nodes
      const layoutedNodes = rfNodes.map((node) => {
        const pos = positions[node.id];
        return {
          ...node,
          position: pos || { x: 0, y: 0 },
        };
      });

      // Add group background nodes for visual sub-recipe grouping
      const groupNodes = Object.entries(groupBounds).map(([groupId, bounds]) => {
        const groupName = groupId.replace("group-", "");
        return {
          id: groupId,
          type: "group",
          position: { x: bounds.x, y: bounds.y },
          style: {
            width: bounds.width,
            height: bounds.height,
            backgroundColor: "rgba(0,0,0,0.03)",
            border: "1px dashed rgba(0,0,0,0.15)",
            borderRadius: "12px",
            padding: "8px",
            zIndex: -1,
          },
          data: {
            label: groupName,
          },
          selectable: false,
          draggable: false,
        };
      });

      return [...groupNodes, ...layoutedNodes];
    } catch (error) {
      console.error("ELK layout failed, falling back to simple layout:", error);
      // Simple fallback: stack nodes vertically
      return rfNodes.map((node, i) => ({
        ...node,
        position: { x: (i % 4) * 300, y: Math.floor(i / 4) * 200 },
      }));
    }
  }, []);

  React.useEffect(() => {
    if (!recipe) {
      setNodes([]);
      setEdges([]);
      return;
    }

    // Get sub-recipes
    const subRecipes = recipe.subRecipes || [];

    // Build graph data
    const { nodes: allRawNodes, edges: allEdges, nodeSubRecipeMap } =
      prepareGraphDataUnified(subRecipes, recipe, "graph");

    // Add calculated height to action nodes
    const allNodes = allRawNodes.map((node) => {
      if (node.type === "action") {
        return {
          ...node,
          data: { ...node.data, height: calculateNodeHeight(node) },
        };
      }
      return node;
    });

    // Build React Flow nodes (unpositioned)
    const rfNodes = allNodes.map((node) => ({
      id: node.id,
      type: "custom",
      position: { x: 0, y: 0 },
      data: {
        label: node.label,
        type: node.type,
        time: node.time,
        tools: node.tools,
        quantity: node.quantity,
        isCompleted: completedSteps[node.id] || false,
        height: node.data?.height || (node.type === "action" ? calculateNodeHeight(node) : 60),
        state: node.state,
      },
    }));

    // Run ELK layout (async)
    layoutGraph(rfNodes, allEdges, nodeSubRecipeMap).then((layoutedNodes) => {
      setNodes(layoutedNodes);
      setEdges(allEdges);
    });
  }, [recipe, completedSteps, setNodes, setEdges, layoutGraph]);

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        position: "relative",
        bgcolor: "background.default",
        minHeight: "500px",
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
        fitViewOptions={{ padding: 0.2 }}
        style={{ background: "transparent", flex: 1 }}
        minZoom={0.05}
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
