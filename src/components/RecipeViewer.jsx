import React, { useState } from "react";
import {
  Box,
  Container,
  Typography,
  Button,
  Paper,
  Chip,
  Stack,
  Divider,
} from "@mui/material";
import {
  ChefHat,
  Clock,
  Thermometer,
  Utensils,
  CakeSlice,
  ArrowRight,
  Target,
} from "lucide-react";
import RecipeFlow from "./RecipeFlow";
import recipeData from "../data/recipeFlow.json";

export default function RecipeViewer() {
  const [selectedPrep, setSelectedPrep] = useState("creme-italienne");

  const recipes = recipeData.components;

  // Fonction pour obtenir les labels des ingrédients à partir de leurs IDs
  const getIngredientLabels = (edge, nodes) => {
    const sourceIds = Array.isArray(edge.from) ? edge.from : [edge.from];
    return sourceIds
      .map((id) => {
        const node = nodes[id];
        if (node && node.type === "ingredient") {
          return {
            label: node.label,
            quantity: node.quantity,
            type: "ingredient",
          };
        } else if (node && node.type === "state") {
          return { label: node.label, type: "state" };
        }
        return null;
      })
      .filter(Boolean);
  };

  // Fonction pour obtenir l'état de sortie
  const getOutputState = (edge, nodes) => {
    const targetIds = Array.isArray(edge.to) ? edge.to : [edge.to];
    return targetIds.map((id) => nodes[id]).filter(Boolean)[0];
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography
        variant="h4"
        gutterBottom
        sx={{ display: "flex", alignItems: "center", gap: 2 }}
      >
        <ChefHat />
        {recipeData.title}
      </Typography>

      <Box sx={{ display: "flex", gap: 2, mb: 4 }}>
        {Object.entries(recipes).map(([key, recipe]) => (
          <Button
            key={key}
            variant={selectedPrep === key ? "contained" : "outlined"}
            onClick={() => setSelectedPrep(key)}
            sx={{ textTransform: "none" }}
          >
            {recipe.title}
          </Button>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
        <Box>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              {recipes[selectedPrep].title}
            </Typography>

            {recipes[selectedPrep].warning && (
              <Box
                sx={{
                  bgcolor: "warning.light",
                  color: "warning.dark",
                  p: 2,
                  borderRadius: 1,
                  mb: 3,
                }}
              >
                {recipes[selectedPrep].warning}
              </Box>
            )}

            <Box sx={{ mb: 4 }}>
              <Typography
                variant="h6"
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
              >
                <Utensils />
                Ingrédients nécessaires
              </Typography>
              <Box
                sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}
              >
                {Object.entries(recipes[selectedPrep].nodes)
                  .filter(([_, node]) => node.type === "ingredient")
                  .map(([id, node]) => (
                    <Chip
                      key={id}
                      label={`${node.label} (${node.quantity})`}
                      variant="outlined"
                      sx={{
                        bgcolor: "#e3f2fd",
                        borderColor: "#90caf9",
                      }}
                    />
                  ))}
              </Box>
            </Box>

            <Typography variant="h6" gutterBottom>
              Étapes de préparation
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {recipes[selectedPrep].edges.map((edge, index) => (
                <Paper
                  key={index}
                  variant="outlined"
                  sx={{
                    p: 2,
                    borderColor: "divider",
                    "&:hover": {
                      borderColor: "primary.main",
                      boxShadow: 1,
                    },
                  }}
                >
                  {/* En-tête de l'étape */}
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      mb: 2,
                    }}
                  >
                    <Typography variant="h6" color="primary">
                      Étape {index + 1}
                    </Typography>
                    <Box sx={{ display: "flex", gap: 2 }}>
                      {edge.temperature && (
                        <Chip
                          icon={<Thermometer size={16} />}
                          label={edge.temperature}
                          size="small"
                          sx={{ bgcolor: "#fff3e0" }}
                        />
                      )}
                      {edge.time && (
                        <Chip
                          icon={<Clock size={16} />}
                          label={edge.time}
                          size="small"
                          sx={{ bgcolor: "#f3e5f5" }}
                        />
                      )}
                    </Box>
                  </Box>

                  {/* Action principale */}
                  <Typography
                    variant="subtitle1"
                    sx={{
                      mb: 2,
                      fontWeight: 500,
                      color: "text.primary",
                      bgcolor: "action.hover",
                      p: 1,
                      borderRadius: 1,
                    }}
                  >
                    {edge.action}
                  </Typography>

                  <Stack spacing={2}>
                    {/* Ingrédients et états d'entrée */}
                    <Box>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 0.5,
                          mb: 1,
                        }}
                      >
                        <CakeSlice size={16} />
                        Ingrédients et préparations utilisés
                      </Typography>
                      <Stack
                        direction="row"
                        spacing={1}
                        flexWrap="wrap"
                        gap={1}
                      >
                        {getIngredientLabels(
                          edge,
                          recipes[selectedPrep].nodes
                        ).map((item, idx) => (
                          <Chip
                            key={idx}
                            label={
                              item.type === "ingredient"
                                ? `${item.label} (${item.quantity})`
                                : item.label
                            }
                            size="small"
                            variant="outlined"
                            sx={{
                              bgcolor:
                                item.type === "ingredient"
                                  ? "#e3f2fd"
                                  : "#f3e5f5",
                              borderColor:
                                item.type === "ingredient"
                                  ? "#90caf9"
                                  : "#ce93d8",
                            }}
                          />
                        ))}
                      </Stack>
                    </Box>

                    {/* Ustensiles */}
                    <Box>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 0.5,
                          mb: 1,
                        }}
                      >
                        <Utensils size={16} />
                        Ustensiles nécessaires
                      </Typography>
                      <Stack
                        direction="row"
                        spacing={1}
                        flexWrap="wrap"
                        gap={1}
                      >
                        {edge.tools.map((tool, idx) => (
                          <Chip
                            key={idx}
                            label={tool}
                            size="small"
                            variant="outlined"
                            sx={{
                              bgcolor: "#fff3e0",
                              borderColor: "#ffb74d",
                            }}
                          />
                        ))}
                      </Stack>
                    </Box>

                    {/* État de sortie */}
                    <Box>
                      <Divider sx={{ my: 1 }}>
                        <Chip
                          icon={<ArrowRight size={16} />}
                          label="Résultat obtenu"
                          size="small"
                        />
                      </Divider>
                      <Box
                        sx={{
                          mt: 1,
                          p: 1.5,
                          bgcolor: "#f3e5f5",
                          borderRadius: 1,
                          border: "1px dashed #ce93d8",
                        }}
                      >
                        <Typography
                          variant="subtitle2"
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1,
                          }}
                        >
                          <Target size={16} />
                          {
                            getOutputState(edge, recipes[selectedPrep].nodes)
                              ?.label
                          }
                        </Typography>
                      </Box>
                    </Box>
                  </Stack>
                </Paper>
              ))}
            </Box>
          </Paper>
        </Box>

        <RecipeFlow selectedComponent={selectedPrep} />
      </Box>
    </Container>
  );
}
