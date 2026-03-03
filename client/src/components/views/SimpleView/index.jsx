import React, { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useReactToPrint } from "react-to-print";
import { useRecipe } from "../../../contexts/RecipeContext";
import RecipeHeader from "./RecipeHeader";
import IngredientsList from "./IngredientsList/index";
import PreparationSteps from "./PreparationSteps";
import { Box, Container, Paper, Divider, Typography } from "@mui/material";

const SimpleView = () => {
  const { recipe } = useRecipe();
  const { t } = useTranslation();
  const [shoppingMode, setShoppingMode] = useState(false);
  const printRef = useRef(null);

  const handlePrint = useReactToPrint({
    contentRef: printRef,
    documentTitle: recipe?.metadata?.title,
    pageStyle: `
      @page { margin: 0; size: A4; }
      @media print {
        body {
          background: white !important;
          margin: 0 !important;
          padding: 1.8cm 1.5cm !important;
        }
        *, *::before, *::after {
          background-color: transparent !important;
          box-shadow: none !important;
          text-shadow: none !important;
          color: #222 !important;
        }
        hr, [class*="MuiDivider"] {
          border-color: #ddd !important;
        }
      }
    `,
  });

  const nutrition = recipe?.metadata?.nutritionPerServing;
  const hasNutrition =
    nutrition && nutrition.calories && nutrition.confidence !== "none";

  return (
    <Box
      sx={{
        height: "calc(100vh - 64px)",
        overflow: "auto",
        p: { xs: 0, sm: 3, md: 4 },
        pt: { xs: 2, sm: 3, md: 4 },
        "@keyframes fadeIn": {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 },
        },
        animation: "fadeIn 0.3s ease-in-out",
        "@media print": {
          height: "auto",
          overflow: "visible",
          p: 0,
          animation: "none",
        },
      }}
    >
      <Container
        sx={{
          maxWidth: "1000px !important",
          display: "flex",
          flexDirection: "column",
          gap: 3,
          mb: 9,
          "@media print": {
            maxWidth: "100% !important",
            mb: 0,
          },
        }}
      >
        <Paper
          ref={printRef}
          elevation={2}
          sx={{
            p: { xs: 3, sm: 4 },
            borderRadius: 2,
            "@media print": {
              boxShadow: "none",
              borderRadius: 0,
              p: 0,
            },
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
              "@media print": { gap: 1.5 },
            }}
          >
            <RecipeHeader recipe={recipe} onPrint={handlePrint} />

            {/* Print-only nutrition summary — right after header */}
            {hasNutrition && (
              <Box
                sx={{
                  display: "none",
                  "@media print": {
                    display: "block",
                    mt: -0.5,
                  },
                }}
              >
                <Typography
                  sx={{
                    fontSize: "9px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.12em",
                    mb: 1,
                  }}
                >
                  {t("nutrition.perServingSection")}
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    gap: 3,
                    fontSize: "10px",
                    lineHeight: 1.6,
                  }}
                >
                  <Box>
                    <Typography
                      sx={{
                        fontSize: "18px",
                        fontWeight: 700,
                        lineHeight: 1.1,
                      }}
                    >
                      {Math.round(nutrition.calories)}
                    </Typography>
                    <Typography sx={{ fontSize: "8px", letterSpacing: "0.05em" }}>
                      kcal
                    </Typography>
                  </Box>
                  {[
                    {
                      key: "protein",
                      label: t("nutrition.macroProtein"),
                      value: nutrition.protein,
                    },
                    {
                      key: "carbs",
                      label: t("nutrition.macroCarbs"),
                      value: nutrition.carbs,
                    },
                    {
                      key: "fat",
                      label: t("nutrition.macroFat"),
                      value: nutrition.fat,
                    },
                    {
                      key: "fiber",
                      label: t("nutrition.macroFiber"),
                      value: nutrition.fiber,
                    },
                  ]
                    .filter((m) => m.value != null)
                    .map((m) => (
                      <Box key={m.key} sx={{ textAlign: "center" }}>
                        <Typography
                          sx={{
                            fontSize: "14px",
                            fontWeight: 600,
                            lineHeight: 1.1,
                          }}
                        >
                          {Math.round(m.value)}g
                        </Typography>
                        <Typography
                          sx={{
                            fontSize: "8px",
                            letterSpacing: "0.05em",
                            textTransform: "lowercase",
                          }}
                        >
                          {m.label}
                        </Typography>
                      </Box>
                    ))}
                </Box>
              </Box>
            )}

            <Divider sx={{ borderStyle: "dashed", "@media print": { display: "none" } }} />
            <IngredientsList
              recipe={recipe}
              shoppingMode={shoppingMode}
              setShoppingMode={setShoppingMode}
            />
            <Divider sx={{ borderStyle: "dashed", "@media print": { display: "none" } }} />
            <PreparationSteps recipe={recipe} />
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default SimpleView;
