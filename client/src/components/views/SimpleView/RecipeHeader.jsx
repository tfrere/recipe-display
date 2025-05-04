import React, { useState, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Box,
  Button,
  IconButton,
  Typography,
  useTheme,
  Link,
  Collapse,
} from "@mui/material";
import KeyboardBackspaceOutlinedIcon from "@mui/icons-material/KeyboardBackspaceOutlined";
import PrintOutlinedIcon from "@mui/icons-material/PrintOutlined";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import GroupOutlinedIcon from "@mui/icons-material/GroupOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { useRecipe } from "../../../contexts/RecipeContext";
import { useConstants } from "../../../contexts/ConstantsContext";
import RecipeImage from "../../common/RecipeImage";
import TimeDisplay from "../../common/TimeDisplay";
import RecipeTimes from "../../common/RecipeTimes";
import { parseTimeToMinutes } from "../../../utils/timeUtils";
import { copyRecipeToClipboard } from "../../../utils/recipeTextUtils";
import GraphModal from "../../views/GraphView/GraphModal";
import PrintableRecipe from "./PrintableRecipe";
import DeleteConfirmationDialog from "../../common/DeleteConfirmationDialog";

const API_BASE_URL =
  import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

const HEADER_TEXTS = {
  ACTIONS: {
    PRINT: "Print recipe",
    COPY: "Copy recipe",
    RESET: "Reset recipe progress",
    INCREASE_SERVINGS: "Increase servings",
    DECREASE_SERVINGS: "Decrease servings",
    BACK: "Back to recipes",
    SHOW_GRAPH: "Show recipe graph",
    DELETE: "Delete recipe",
  },
  DELETE_DIALOG: {
    TITLE: "Supprimer la recette",
    CONTENT:
      "Êtes-vous sûr de vouloir supprimer cette recette ? Cette action est irréversible.",
    CANCEL: "Annuler",
    CONFIRM: "Supprimer",
  },
  SERVINGS: {
    SINGLE: "1 serving",
    MULTIPLE: (count) => `${count} servings`,
  },
  TOOLS: {
    TITLE: "Tools:",
  },
  NOTES: {
    READ_MORE: "read more",
    READ_LESS: "read less",
    TITLE: "Notes",
  },
};

const overlayStyle = {
  backdropFilter: "blur(8px)",
  backgroundColor: "rgba(0, 0, 0, 0.4)",
  borderRadius: "6px !important",
  boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
  "&:hover": {
    backgroundColor: "rgba(0, 0, 0, 0.6)",
  },
};

// Maximum de caractères à afficher pour l'ensemble des notes avant de les tronquer
const MAX_NOTES_PREVIEW_LENGTH = 250;

const RecipeHeader = ({ recipe }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    updateServings,
    currentServings,
    resetServings,
    getRemainingTime,
    calculateTotalTime,
    calculateTotalCookingTime,
    tools,
  } = useRecipe();
  const { darkMode, toggleDarkMode } = useTheme();
  const theme = useTheme();
  const { constants } = useConstants();
  const [openGraph, setOpenGraph] = useState(false);
  const [imageRatio, setImageRatio] = useState(1);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [expandedNotes, setExpandedNotes] = useState(false);

  // Attendre que les constantes soient chargées
  if (!constants) {
    return null;
  }

  const seasonText = useMemo(() => {
    return Array.isArray(recipe.seasons) && recipe.seasons.length > 0
      ? recipe.seasons.join(", ")
      : "All Seasons";
  }, [recipe.seasons]);

  const RECIPE_TYPE_LABELS = Object.fromEntries(
    constants.recipe_types.map((type) => [type.id, type.label])
  );
  const DIET_LABELS = Object.fromEntries(
    constants.diets.map((diet) => [diet.id, diet.label])
  );
  const SEASON_LABELS = Object.fromEntries(
    constants.seasons.map((season) => [season.id, season.label])
  );

  // Déstructurer les propriétés de la recette
  const { metadata = {} } = recipe || {};

  // Calculer la longueur totale des notes et si elles sont longues
  const allNotesText = metadata.notes && metadata.notes.join("\n\n");
  const isLongNotes =
    allNotesText && allNotesText.length > MAX_NOTES_PREVIEW_LENGTH;

  // Préparation de l'aperçu des notes
  const notesPreview = isLongNotes
    ? allNotesText.substring(0, MAX_NOTES_PREVIEW_LENGTH) + "..."
    : allNotesText;

  const handleImageLoad = (ratio) => {
    setImageRatio(ratio);
  };

  const handleServingsChange = (delta) => {
    const newServings = currentServings + delta;
    if (newServings >= 1) {
      updateServings(newServings);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDeleteClick = () => {
    setOpenDeleteDialog(true);
  };

  const handleDeleteCancel = () => {
    setOpenDeleteDialog(false);
  };

  const handleDeleteConfirm = async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/recipes/${recipe.slug}`,
        {
          method: "DELETE",
        }
      );
      if (response.ok) {
        setOpenDeleteDialog(false);
        navigate("/");
      } else {
        console.error("Failed to delete recipe");
      }
    } catch (error) {
      console.error("Error deleting recipe:", error);
    }
  };

  if (!recipe) {
    return null;
  }

  return (
    <>
      <PrintableRecipe recipe={recipe} />
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: 2,
          width: "100%",
          maxWidth: "100%",
          "@media print": {
            display: "none",
          },
        }}
      >
        {/* Recipe Header Content */}
        <Box sx={{ width: "100%" }}>
          {/* Title and Image Section */}
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              gap: { xs: 3, md: 6 },
              mb: 3,
              width: "100%",
            }}
          >
            {/* Square Image */}
            <Box
              sx={{
                width: "100%",
                maxWidth: { xs: "100%", md: 360 },
                maxHeight: 520,
                height: "auto",
                aspectRatio: "1 / 1",
                flexShrink: 0,
                position: "relative",
                borderRadius: 2,
                overflow: "hidden",
                boxShadow: (theme) =>
                  theme.palette.mode === "dark"
                    ? "0 12px 24px rgba(0, 0, 0, 0.3)"
                    : "0 12px 24px rgba(0, 0, 0, 0.1)",
                "&::after": {
                  content: '""',
                  position: "absolute",
                  inset: 0,
                  background: (theme) => `linear-gradient(to bottom, 
                  ${
                    theme.palette.mode === "dark"
                      ? "rgba(0, 0, 0, 0.2)"
                      : "rgba(255, 255, 255, 0.1)"
                  } 0%,
                  transparent 40%,
                  ${
                    theme.palette.mode === "dark"
                      ? "rgba(0, 0, 0, 0.4)"
                      : "rgba(0, 0, 0, 0.2)"
                  } 100%)`,
                  pointerEvents: "none",
                },
              }}
            >
              <RecipeImage
                slug={recipe.slug}
                title={recipe.title}
                size="original"
                onLoad={handleImageLoad}
              />
              {/* Back button overlay */}
              <Button
                onClick={() => navigate("/")}
                startIcon={<KeyboardBackspaceOutlinedIcon />}
                sx={{
                  position: "absolute",
                  top: 16,
                  left: 16,
                  textTransform: "none",
                  color: "white",
                  padding: "6px 12px",
                  ...overlayStyle,
                }}
              >
                {HEADER_TEXTS.ACTIONS.BACK}
              </Button>
              {/* Print and Copy buttons overlay */}
              <Box
                sx={{
                  position: "absolute",
                  top: 16,
                  right: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1,
                }}
              >
                <IconButton
                  onClick={handlePrint}
                  size="medium"
                  title={HEADER_TEXTS.ACTIONS.PRINT}
                  sx={{
                    color: "white",
                    padding: "12px",
                    ...overlayStyle,
                    "& .MuiSvgIcon-root": {
                      fontSize: "1.3rem",
                    },
                  }}
                >
                  <PrintOutlinedIcon />
                </IconButton>
                <IconButton
                  onClick={() => copyRecipeToClipboard(recipe)}
                  size="medium"
                  title={HEADER_TEXTS.ACTIONS.COPY}
                  sx={{
                    color: "white",
                    padding: "12px",
                    ...overlayStyle,
                    "& .MuiSvgIcon-root": {
                      fontSize: "1.3rem",
                    },
                  }}
                >
                  <ContentCopyOutlinedIcon />
                </IconButton>
                <IconButton
                  onClick={() => setOpenGraph(true)}
                  size="medium"
                  title={HEADER_TEXTS.ACTIONS.SHOW_GRAPH}
                  sx={{
                    color: "white",
                    padding: "12px",
                    ...overlayStyle,
                    "& .MuiSvgIcon-root": {
                      fontSize: "1.3rem",
                    },
                  }}
                >
                  <AccountTreeOutlinedIcon />
                </IconButton>
                <IconButton
                  onClick={handleDeleteClick}
                  size="medium"
                  title={HEADER_TEXTS.ACTIONS.DELETE}
                  sx={{
                    color: "white",
                    padding: "12px",
                    ...overlayStyle,
                    "& .MuiSvgIcon-root": {
                      fontSize: "1.3rem",
                    },
                  }}
                >
                  <DeleteOutlineIcon />
                </IconButton>
              </Box>
              {/* Time overlay */}
              {(calculateTotalTime(recipe) ||
                calculateTotalCookingTime(recipe)) && (
                <Box
                  sx={{
                    position: "absolute",
                    bottom: 16,
                    left: 16,
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    padding: "6px 12px",
                    ...overlayStyle,
                    zIndex: 1,
                  }}
                >
                  {/* Temps de cuisson */}
                  <RecipeTimes
                    totalTime={calculateTotalTime(recipe)}
                    totalCookingTime={calculateTotalCookingTime(recipe)}
                    iconSize="small"
                    sx={{
                      color: "white",
                      fontWeight: 500,
                      fontSize: "0.9rem",
                    }}
                  />
                </Box>
              )}
            </Box>

            {/* Info Column */}
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 2,
                alignItems: "flex-start",
                flex: 1,
                pt: 2,
              }}
            >
              {/* Title and Description */}
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  width: "100%",
                  "@media print": { display: "none" },
                }}
              >
                {/* Title */}
                <Typography
                  variant="h3"
                  component="h1"
                  sx={{
                    fontWeight: 700,
                    fontSize: "2rem",
                    mb: 2,
                  }}
                >
                  {recipe.metadata.title}
                </Typography>

                {/* Description si elle existe */}
                {recipe.metadata.description && (
                  <Typography
                    variant="body1"
                    color="text.secondary"
                    sx={{
                      lineHeight: 1.6,
                      fontSize: "1rem",
                      mb: 2,
                    }}
                  >
                    {recipe.metadata.description}
                  </Typography>
                )}

                {/* Recipe Metadata - Maintenant indépendant de la description */}
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {/* Diet, Season, Type */}
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      fontWeight: 500,
                      textTransform: "capitalize",
                      letterSpacing: "0.02em",
                      color: "text.primary",
                      opacity: 0.75,
                      fontSize: "0.9rem",
                    }}
                  >
                    {DIET_LABELS[metadata.diets?.[0]] || "Normal"}
                    {" • "}
                    {seasonText}
                    {" • "}
                    {RECIPE_TYPE_LABELS[metadata.recipeType] ||
                      RECIPE_TYPE_LABELS[metadata.type] ||
                      "Main"}
                  </Typography>

                  {/* Source Info */}
                  {(metadata.nationality ||
                    metadata.author ||
                    metadata.bookTitle ||
                    metadata.sourceUrl) && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        fontStyle: "italic",
                        opacity: 0.6,
                        letterSpacing: "0.01em",
                        fontSize: "0.85rem",
                      }}
                    >
                      {[
                        metadata.nationality &&
                          `${metadata.nationality} cuisine`,
                        metadata.author && `By ${metadata.author}`,
                        metadata.bookTitle && `From "${metadata.bookTitle}"`,
                        metadata.sourceUrl && (
                          <Link
                            href={metadata.sourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            sx={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 0.5,
                              color: "inherit",
                              textDecoration: "none",
                              "&:hover": {
                                textDecoration: "underline",
                              },
                            }}
                          >
                            Source
                            <OpenInNewIcon sx={{ fontSize: "0.9rem" }} />
                          </Link>
                        ),
                      ]
                        .filter(Boolean)
                        .map((item, index, array) => (
                          <React.Fragment key={index}>
                            {item}
                            {index < array.length - 1 && " • "}
                          </React.Fragment>
                        ))}
                    </Typography>
                  )}

                  {/* Notes en accordéon */}
                  {metadata.notes &&
                    Array.isArray(metadata.notes) &&
                    metadata.notes.length > 0 && (
                      <Box sx={{ mt: 2, mb: 1 }}>
                        <Typography
                          variant="body2"
                          component="div"
                          sx={{
                            fontWeight: 500,
                            color: "text.primary",
                            opacity: 0.8,
                            fontSize: "0.9rem",
                            mb: 1,
                          }}
                        >
                          {HEADER_TEXTS.NOTES.TITLE}
                        </Typography>

                        {/* Notes avec transition fluide */}
                        <Box>
                          {/* Premier paragraphe toujours visible */}
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              whiteSpace: "pre-wrap",
                              fontStyle: "italic",
                              opacity: 0.7,
                              fontSize: "0.875rem",
                              lineHeight: 1.5,
                            }}
                          >
                            {metadata.notes[0]}
                          </Typography>

                          {/* Notes supplémentaires avec collapse */}
                          {metadata.notes.length > 1 && (
                            <>
                              <Collapse in={expandedNotes}>
                                <Box sx={{ mt: 1.5 }}>
                                  {metadata.notes
                                    .slice(1)
                                    .map((note, index) => (
                                      <Typography
                                        key={index}
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{
                                          whiteSpace: "pre-wrap",
                                          fontStyle: "italic",
                                          opacity: 0.7,
                                          fontSize: "0.875rem",
                                          lineHeight: 1.5,
                                          mb:
                                            index < metadata.notes.length - 2
                                              ? 1.5
                                              : 0,
                                        }}
                                      >
                                        {note}
                                      </Typography>
                                    ))}
                                </Box>
                              </Collapse>

                              {/* Bouton pour afficher plus/moins */}
                              <Typography
                                component="span"
                                variant="body2"
                                onClick={() => setExpandedNotes(!expandedNotes)}
                                sx={{
                                  color: "primary.text",
                                  cursor: "pointer",
                                  fontStyle: "italic",
                                  mt: 1.5,
                                  display: "inline-block",
                                  textDecoration: "underline",
                                }}
                              >
                                {expandedNotes
                                  ? HEADER_TEXTS.NOTES.READ_LESS
                                  : HEADER_TEXTS.NOTES.READ_MORE}
                              </Typography>
                            </>
                          )}
                        </Box>
                      </Box>
                    )}
                </Box>
              </Box>

              {/* Bottom Actions */}
              <Box
                sx={{
                  mt: "auto",
                  pt: 2,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1,
                  width: "100%",
                }}
              >
                {/* Servings Controls */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                  }}
                >
                  <Button
                    onClick={() => handleServingsChange(-1)}
                    disabled={currentServings <= 1}
                    size="small"
                    variant="outlined"
                    sx={{
                      minWidth: 0,
                      p: 0.5,
                      borderColor: "divider",
                      color: "text.secondary",
                      "&:hover": {
                        borderColor: "action.hover",
                        backgroundColor: "action.hover",
                      },
                      "&.Mui-disabled": {
                        borderColor: "divider",
                        color: "text.disabled",
                      },
                    }}
                  >
                    <RemoveIcon fontSize="small" />
                  </Button>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      minWidth: 120,
                      justifyContent: "center",
                    }}
                  >
                    {currentServings === 1 ? (
                      <PersonOutlineIcon
                        sx={{
                          color: "text.secondary",
                          fontSize: 20,
                        }}
                      />
                    ) : (
                      <GroupOutlinedIcon
                        sx={{
                          color: "text.secondary",
                          fontSize: 20,
                        }}
                      />
                    )}
                    <Typography variant="body2" color="text.secondary">
                      {currentServings === 1
                        ? HEADER_TEXTS.SERVINGS.SINGLE
                        : HEADER_TEXTS.SERVINGS.MULTIPLE(currentServings)}
                    </Typography>
                  </Box>
                  <Button
                    onClick={() => handleServingsChange(1)}
                    size="small"
                    variant="outlined"
                    sx={{
                      minWidth: 0,
                      p: 0.5,
                      borderColor: "divider",
                      color: "text.secondary",
                      "&:hover": {
                        borderColor: "action.hover",
                        backgroundColor: "action.hover",
                      },
                    }}
                  >
                    <AddIcon fontSize="small" />
                  </Button>
                  {currentServings !== recipe.metadata.servings && (
                    <Button
                      onClick={resetServings}
                      variant="outlined"
                      size="small"
                      startIcon={<RestartAltIcon />}
                      sx={{
                        ml: 1,
                        borderColor: "divider",
                        color: "text.secondary",
                        textTransform: "none",
                        "&:hover": {
                          borderColor: "action.hover",
                          backgroundColor: "action.hover",
                        },
                      }}
                    >
                      Reset
                    </Button>
                  )}
                </Box>
              </Box>
            </Box>
          </Box>
        </Box>
      </Box>

      <DeleteConfirmationDialog
        open={openDeleteDialog}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        recipeName={recipe?.title}
      />

      <GraphModal
        open={openGraph}
        onClose={() => setOpenGraph(false)}
        recipe={recipe}
      />
    </>
  );
};

export default RecipeHeader;
