import React, { memo } from "react";
import { Box, Card, CardContent, Typography, IconButton, Tooltip } from "@mui/material";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import LockOpenOutlinedIcon from "@mui/icons-material/LockOpenOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";
import RecipeImage from "../../common/RecipeImage";
import { formatTimeCompact } from "../../../utils/timeUtils";

const REASON_CONFIG = {
  seasonal: { label: "Seasonal", color: "#4caf50" },
  variety: { label: "Variety", color: "#ff9800" },
  balanced: { label: "Balanced", color: "#7e57c2" },
  "high-protein": { label: "Protein", color: "#66bb6a" },
  "low-calorie": { label: "Light", color: "#26a69a" },
  "high-fiber": { label: "Fiber", color: "#8d6e63" },
};

const ReasonDot = ({ reason, sharedCount }) => {
  if (reason.includes("_shared")) {
    const count = sharedCount || parseInt(reason);
    return (
      <Tooltip title={`${count} shared ingredients`} arrow>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.5,
          }}
        >
          <Box
            sx={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              bgcolor: "primary.main",
              flexShrink: 0,
            }}
          />
          <Typography
            variant="caption"
            sx={{ fontSize: "0.7rem", color: "text.secondary", fontWeight: 500 }}
          >
            {count} shared
          </Typography>
        </Box>
      </Tooltip>
    );
  }

  const cfg = REASON_CONFIG[reason];
  if (!cfg) return null;

  return (
    <Tooltip title={cfg.label} arrow>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.5,
        }}
      >
        <Box
          sx={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            bgcolor: cfg.color,
            flexShrink: 0,
          }}
        />
        <Typography
          variant="caption"
          sx={{ fontSize: "0.7rem", color: "text.secondary", fontWeight: 500 }}
        >
          {cfg.label}
        </Typography>
      </Box>
    </Tooltip>
  );
};

const MealPlannerRecipeCard = memo(({ item, isLocked, onToggleLock, onSwap }) => {
  const { recipe, reasons, sharedCount } = item;
  const totalTime = recipe.totalTimeMinutes || recipe.totalTime || recipe.totalCookingTime || 0;
  const nutrition = recipe.nutritionPerServing;
  const hasCalories = nutrition && nutrition.confidence !== "none" && nutrition.calories > 0;

  const displayReasons = reasons
    .filter((r) => r !== "locked")
    .slice(0, 2);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={recipe.slug}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        style={{ height: "100%" }}
      >
        <Card
          sx={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
            position: "relative",
            overflow: "hidden",
            backgroundColor: "background.paper",
            boxShadow: "rgba(0, 0, 0, 0.04) 0px 3px 5px",
            border: "1px solid",
            borderColor: isLocked ? "text.primary" : "divider",
            borderWidth: isLocked ? 2 : 1,
            transition: "all 0.2s ease-in-out",
            "&:hover": {
              boxShadow:
                "rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.05) 0px 4px 6px -2px",
              "& .card-actions": { opacity: 1 },
            },
          }}
        >
          {/* Image */}
          <Box
            component={Link}
            to={`/recipe/${recipe.slug}`}
            sx={{
              position: "relative",
              paddingTop: "65%",
              width: "100%",
              overflow: "hidden",
              bgcolor: "grey.100",
              display: "block",
              textDecoration: "none",
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
              }}
            />

            {/* Actions overlay — top-right */}
            <Box
              className="card-actions"
              sx={{
                position: "absolute",
                top: 8,
                right: 8,
                display: "flex",
                gap: 0.5,
                opacity: { xs: 1, sm: 0 },
                transition: "opacity 0.2s ease",
              }}
            >
              <IconButton
                size="small"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onToggleLock();
                }}
                sx={{
                  backdropFilter: "blur(8px)",
                  backgroundColor: isLocked ? "rgba(255,255,255,0.95)" : "rgba(0,0,0,0.5)",
                  color: isLocked ? "text.primary" : "white",
                  width: 30,
                  height: 30,
                  "&:hover": {
                    backgroundColor: isLocked ? "rgba(255,255,255,1)" : "rgba(0,0,0,0.7)",
                  },
                }}
              >
                {isLocked ? (
                  <LockOutlinedIcon sx={{ fontSize: "0.9rem" }} />
                ) : (
                  <LockOpenOutlinedIcon sx={{ fontSize: "0.9rem" }} />
                )}
              </IconButton>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onSwap();
                }}
                disabled={isLocked}
                sx={{
                  backdropFilter: "blur(8px)",
                  backgroundColor: "rgba(0,0,0,0.5)",
                  color: "white",
                  width: 30,
                  height: 30,
                  opacity: isLocked ? 0.3 : 1,
                  "&:hover": {
                    backgroundColor: "rgba(0,0,0,0.7)",
                  },
                }}
              >
                <SwapHorizIcon sx={{ fontSize: "0.9rem" }} />
              </IconButton>
            </Box>
          </Box>

          {/* Content */}
          <CardContent
            sx={{
              flex: "1 1 auto",
              display: "flex",
              flexDirection: "column",
              p: 1.5,
              "&:last-child": { pb: 1.5 },
            }}
          >
            {/* Title */}
            <Typography
              component={Link}
              to={`/recipe/${recipe.slug}`}
              variant="subtitle1"
              sx={{
                fontWeight: 600,
                fontSize: "0.9rem",
                lineHeight: 1.3,
                mb: 0.5,
                textDecoration: "none",
                color: "text.primary",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
                textOverflow: "ellipsis",
                "&:hover": { color: "primary.main" },
              }}
            >
              {recipe.title}
            </Typography>

            {/* Reason dots — subtle inline indicators */}
            {displayReasons.length > 0 && (
              <Box sx={{ display: "flex", gap: 1.5, mb: 0.5 }}>
                {displayReasons.map((reason, i) => (
                  <ReasonDot key={i} reason={reason} sharedCount={sharedCount} />
                ))}
              </Box>
            )}

            {/* Footer: time + calories */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                mt: "auto",
                pt: 0.5,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <AccessTimeOutlinedIcon
                  sx={{ fontSize: "0.85rem", color: "text.disabled" }}
                />
                <Typography
                  variant="body2"
                  sx={{ color: "text.secondary", fontSize: "0.78rem" }}
                >
                  {formatTimeCompact(totalTime)}
                </Typography>
              </Box>
              {hasCalories && (
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.3 }}>
                  <LocalFireDepartmentIcon
                    sx={{ fontSize: "0.8rem", color: "#ff9800" }}
                  />
                  <Typography
                    variant="body2"
                    sx={{ color: "text.secondary", fontSize: "0.75rem", fontWeight: 500 }}
                  >
                    {Math.round(nutrition.calories)} kcal
                  </Typography>
                </Box>
              )}
            </Box>
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
});

export default MealPlannerRecipeCard;
