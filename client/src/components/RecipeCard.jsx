import React, { memo, useMemo } from "react";
import { Box, Card, CardContent, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import RecipeImage from "./common/RecipeImage";
import BoltIcon from "@mui/icons-material/Bolt";
import KitchenOutlinedIcon from "@mui/icons-material/KitchenOutlined";
import TimeDisplay from "./common/TimeDisplay";
import { parseTimeToMinutes } from "../utils/timeUtils";

// Extraire les composants qui ne changent pas pour éviter les re-rendus
const QuickRecipeBadge = memo(() => (
  <Box
    sx={{
      position: "absolute",
      top: 12,
      right: 12,
      display: "flex",
      alignItems: "center",
      padding: "6px",
      borderRadius: "8px",
      backdropFilter: "blur(8px)",
      backgroundColor: "rgba(0, 0, 0, 0.4)",
      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
    }}
  >
    <BoltIcon sx={{ fontSize: "1.2rem", color: "white" }} />
  </Box>
));

const RecipeCard = memo(
  ({ recipe, style }) => {
    // Mémoriser les calculs qui ne changent pas pour ce recipe
    const ingredientsCount = useMemo(() => {
      // Vérifier si recipe.ingredients est un tableau ou un objet
      if (Array.isArray(recipe.ingredients)) {
        return recipe.ingredients.length;
      } else {
        return Object.keys(recipe.ingredients || {}).length;
      }
    }, [recipe.ingredients]);
    const seasonText = useMemo(() => {
      return Array.isArray(recipe.seasons) && recipe.seasons.length > 0
        ? recipe.seasons.join(", ")
        : "All Seasons";
    }, [recipe.seasons]);

    return (
      <Card
        component={Link}
        to={`/recipe/${recipe.slug}`}
        sx={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          position: "relative",
          overflow: "hidden",
          backgroundColor: "background.paper",
          boxShadow: "rgba(0, 0, 0, 0.04) 0px 3px 5px",
          border: "1px solid",
          borderColor: "divider",
          textDecoration: "none",
          transition: "all 0.2s ease-in-out",
          "&:hover": {
            transform: "translateY(-4px)",
            boxShadow:
              "rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.05) 0px 4px 6px -2px",
          },
          ...style,
        }}
      >
        <Box
          sx={{
            position: "relative",
            paddingTop: "70%",
            width: "100%",
            overflow: "hidden",
            bgcolor: "grey.100",
          }}
        >
          <RecipeImage
            slug={recipe.slug}
            title={recipe.title}
            size="medium"
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              objectFit: "cover",
              backgroundColor: "grey.100",
            }}
          />
          {recipe.quick && <QuickRecipeBadge />}
          {/* Boîte en bas à gauche uniquement si recipe.complexity existe */}
          {recipe.complexity && (
            <Box
              sx={{
                position: "absolute",
                bottom: 8,
                left: 8,
                display: "flex",
                gap: 1,
                alignItems: "center",
                padding: "4px 8px",
                borderRadius: "6px",
                backdropFilter: "blur(8px)",
                backgroundColor: "rgba(0, 0, 0, 0.4)",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
              }}
            >
              {/* Complexité de la recette */}
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <BoltIcon fontSize="small" sx={{ color: "white" }} />
                <Typography
                  variant="body2"
                  sx={{ color: "white", fontWeight: 500 }}
                >
                  {recipe.complexity}
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
        <CardContent
          sx={{
            flex: "1 1 auto",
            display: "flex",
            flexDirection: "column",
            p: 1.5,
            "&:last-child": {
              pb: 1.5,
            },
          }}
        >
          <Typography
            variant="subtitle1"
            component="h2"
            sx={{
              fontWeight: 600,
              fontSize: "0.95rem",
              lineHeight: 1.3,
              mb: 0.75,
              height: "2.6em",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {recipe.title}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              fontSize: "0.8rem",
              mb: 0.5,
            }}
          >
            {recipe.recipeType == "main_course"
              ? "main course"
              : recipe.recipeType}
          </Typography>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              flexWrap: "wrap",
              justifyContent: "flex-end",
              mt: "auto",
            }}
          >
            <Typography
              variant="body2"
              sx={{
                color: "text.secondary",
                fontSize: "0.7rem",
              }}
            >
              {seasonText}
            </Typography>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                ml: "auto",
              }}
            >
              <KitchenOutlinedIcon
                sx={{
                  fontSize: "0.9rem",
                  color: "text.secondary",
                }}
              />
              <Typography
                variant="body2"
                sx={{
                  color: "text.secondary",
                  fontSize: "0.8rem",
                }}
              >
                {ingredientsCount}
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>
    );
  },
  (prevProps, nextProps) => {
    // Comparaison personnalisée pour ne re-rendre que si nécessaire
    return (
      prevProps.recipe.slug === nextProps.recipe.slug &&
      prevProps.style === nextProps.style
    );
  }
);

export default RecipeCard;
