import React, { useState, useCallback } from "react";
import {
  Box,
  TextField,
  Typography,
  Button,
  IconButton,
  Paper,
  Chip,
  Select,
  MenuItem,
  FormControl,
  Tooltip,
  Switch,
  FormControlLabel,
  InputAdornment,
  Alert,
  Collapse,
  LinearProgress,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteOutlineIcon,
  NavigateNext as NextIcon,
  NavigateBefore as BackIcon,
  Restaurant as RestaurantIcon,
  Timer as TimerIcon,
  Thermostat as ThermostatIcon,
  ArrowUpward as ArrowUpIcon,
  ArrowDownward as ArrowDownIcon,
  CheckCircleOutline as CheckIcon,
  Check as CheckSmallIcon,
  LocalOffer as TagIcon,
  MenuBook as MenuBookIcon,
  EggAlt as EggIcon,
  Blender as BlenderIcon,
  DoneAll as DoneAllIcon,
} from "@mui/icons-material";
// ─── Constants ───────────────────────────────────────────────

const UNITS = [
  { value: "g", label: "g" },
  { value: "kg", label: "kg" },
  { value: "ml", label: "ml" },
  { value: "cl", label: "cl" },
  { value: "L", label: "L" },
  { value: "tbsp", label: "tbsp" },
  { value: "tsp", label: "tsp" },
  { value: "piece", label: "piece(s)" },
  { value: "pinch", label: "pinch(es)" },
  { value: "", label: "—" },
];

const CATEGORIES = [
  { value: "produce", label: "Produce" },
  { value: "herb", label: "Fresh Herbs" },
  { value: "meat", label: "Meat" },
  { value: "poultry", label: "Poultry" },
  { value: "seafood", label: "Seafood" },
  { value: "dairy", label: "Dairy" },
  { value: "egg", label: "Eggs" },
  { value: "grain", label: "Grains & Pasta" },
  { value: "legume", label: "Legumes" },
  { value: "nuts_seeds", label: "Nuts & Seeds" },
  { value: "pantry", label: "Pantry" },
  { value: "oil", label: "Oils" },
  { value: "spice", label: "Spices" },
  { value: "condiment", label: "Condiments" },
  { value: "beverage", label: "Beverages" },
  { value: "other", label: "Other" },
];

const RECIPE_TYPES = [
  { value: "appetizer", label: "Appetizer" },
  { value: "starter", label: "Starter" },
  { value: "main_course", label: "Main Course" },
  { value: "dessert", label: "Dessert" },
  { value: "drink", label: "Drink" },
  { value: "base", label: "Base" },
];

const DIFFICULTIES = [
  { value: "easy", label: "Easy", color: "#4caf50" },
  { value: "medium", label: "Medium", color: "#ff9800" },
  { value: "hard", label: "Hard", color: "#f44336" },
];

const STEP_TYPES = [
  { value: "prep", label: "Prep" },
  { value: "combine", label: "Combine" },
  { value: "cook", label: "Cook" },
  { value: "rest", label: "Rest" },
  { value: "serve", label: "Serve" },
];

const WIZARD_STEPS = [
  { label: "Info", Icon: MenuBookIcon },
  { label: "Ingredients", Icon: EggIcon },
  { label: "Steps", Icon: BlenderIcon },
  { label: "Finalize", Icon: DoneAllIcon },
];

const INITIAL_FORM_DATA = {
  title: "",
  description: "",
  servings: 4,
  prepTimeMinutes: 0,
  cookTimeMinutes: 0,
  difficulty: "easy",
  recipeType: "main_course",
  ingredients: [],
  steps: [],
  tags: [],
  notes: [],
  author: "",
  source: "",
  nationality: "",
};

// ─── Helpers ─────────────────────────────────────────────────

function minutesToISO(totalMinutes) {
  if (!totalMinutes || totalMinutes <= 0) return null;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  let iso = "PT";
  if (hours > 0) iso += `${hours}H`;
  if (minutes > 0) iso += `${minutes}M`;
  return iso === "PT" ? null : iso;
}

function formatMinutes(totalMinutes) {
  if (!totalMinutes) return "—";
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h > 0 && m > 0) return `${h}h${String(m).padStart(2, "0")}`;
  if (h > 0) return `${h}h`;
  return `${m} min`;
}

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

function createEmptyIngredient() {
  return {
    _id: generateId(),
    name: "",
    quantity: "",
    unit: "g",
    category: "other",
    preparation: "",
    optional: false,
  };
}

function createEmptyStep() {
  return {
    _id: generateId(),
    action: "",
    stepType: "prep",
    durationMinutes: 0,
    temperature: "",
  };
}

// ─── Custom Stepper ──────────────────────────────────────────

const WizardStepper = ({ activeStep, onStepClick }) => {
  const progressPercent = (activeStep / (WIZARD_STEPS.length - 1)) * 100;

  return (
    <Box sx={{ mb: 3 }}>
      {/* Step indicators */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          position: "relative",
          mb: 1,
        }}
      >
        {WIZARD_STEPS.map((step, index) => {
          const isCompleted = index < activeStep;
          const isActive = index === activeStep;
          const isClickable = index < activeStep;

          return (
            <Box
              key={step.label}
              onClick={() => isClickable && onStepClick(index)}
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 0.5,
                cursor: isClickable ? "pointer" : "default",
                zIndex: 1,
                flex: 1,
              }}
            >
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  bgcolor: isCompleted
                    ? "primary.main"
                    : isActive
                      ? "primary.main"
                      : "grey.100",
                  color: isCompleted || isActive ? "white" : "text.disabled",
                  transition: "all 0.35s cubic-bezier(.4,0,.2,1)",
                  boxShadow: isActive
                    ? "0 2px 12px rgba(25,118,210,0.35)"
                    : "none",
                  "& .MuiSvgIcon-root": { fontSize: 18 },
                }}
              >
                {isCompleted ? (
                  <CheckSmallIcon sx={{ fontSize: 20 }} />
                ) : (
                  <step.Icon sx={{ fontSize: 18 }} />
                )}
              </Box>
              <Typography
                variant="caption"
                sx={{
                  fontWeight: isActive ? 650 : 400,
                  color: isCompleted || isActive ? "text.primary" : "text.disabled",
                  fontSize: "0.7rem",
                  transition: "all 0.3s",
                  textAlign: "center",
                }}
              >
                {step.label}
              </Typography>
            </Box>
          );
        })}
      </Box>

      {/* Progress bar */}
      <LinearProgress
        variant="determinate"
        value={progressPercent}
        sx={{
          height: 3,
          borderRadius: 2,
          bgcolor: "grey.100",
          "& .MuiLinearProgress-bar": {
            borderRadius: 2,
            transition: "transform 0.4s cubic-bezier(.4,0,.2,1)",
          },
        }}
      />
    </Box>
  );
};

// ─── Sub Components ──────────────────────────────────────────

const ServingsInput = ({ value, onChange }) => (
  <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
    <IconButton
      size="small"
      onClick={() => onChange(Math.max(1, value - 1))}
      disabled={value <= 1}
      sx={{
        border: 1,
        borderColor: "divider",
        borderRadius: 1.5,
        width: 30,
        height: 30,
      }}
    >
      <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1 }}>
        −
      </Typography>
    </IconButton>
    <Typography
      variant="h6"
      sx={{ minWidth: 28, textAlign: "center", fontWeight: 700, fontSize: "1.1rem" }}
    >
      {value}
    </Typography>
    <IconButton
      size="small"
      onClick={() => onChange(Math.min(50, value + 1))}
      disabled={value >= 50}
      sx={{
        border: 1,
        borderColor: "divider",
        borderRadius: 1.5,
        width: 30,
        height: 30,
      }}
    >
      <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1 }}>
        +
      </Typography>
    </IconButton>
  </Box>
);

const TimeInput = ({ label, icon, value, onChange }) => {
  const hours = Math.floor(value / 60);
  const minutes = value % 60;

  const setTime = (h, m) => {
    onChange(Math.max(0, Math.min(23, h)) * 60 + Math.max(0, Math.min(59, m)));
  };

  return (
    <Box>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mb: 0.5, display: "flex", alignItems: "center", gap: 0.5 }}
      >
        {icon} {label}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
        <TextField
          type="number"
          size="small"
          value={hours || ""}
          onChange={(e) => setTime(parseInt(e.target.value) || 0, minutes)}
          placeholder="0"
          inputProps={{ min: 0, max: 23, style: { textAlign: "center" } }}
          sx={{ width: 52 }}
        />
        <Typography variant="caption" color="text.secondary">h</Typography>
        <TextField
          type="number"
          size="small"
          value={minutes || ""}
          onChange={(e) => setTime(hours, parseInt(e.target.value) || 0)}
          placeholder="00"
          inputProps={{ min: 0, max: 59, style: { textAlign: "center" } }}
          sx={{ width: 52 }}
        />
        <Typography variant="caption" color="text.secondary">min</Typography>
      </Box>
    </Box>
  );
};

const TagInput = ({ tags, onChange }) => {
  const [inputValue, setInputValue] = useState("");

  const addTag = () => {
    const trimmed = inputValue.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
    }
    setInputValue("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    }
    if (e.key === "Backspace" && !inputValue && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: tags.length > 0 ? 1 : 0 }}>
        {tags.map((tag) => (
          <Chip
            key={tag}
            label={tag}
            size="small"
            onDelete={() => onChange(tags.filter((t) => t !== tag))}
            color="primary"
            variant="outlined"
          />
        ))}
      </Box>
      <TextField
        fullWidth
        size="small"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={addTag}
        placeholder="Type a tag and press Enter..."
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <TagIcon fontSize="small" color="action" />
            </InputAdornment>
          ),
        }}
      />
    </Box>
  );
};

// ─── Step 1: Basic Info ──────────────────────────────────────

const BasicInfoStep = ({ data, onChange }) => {
  const update = (field, value) => onChange({ ...data, [field]: value });

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      <TextField
        fullWidth
        label="Recipe Name"
        value={data.title}
        onChange={(e) => update("title", e.target.value)}
        required
        autoFocus
        placeholder="E.g. Lemon Meringue Pie"
        sx={{ "& .MuiInputBase-input": { fontSize: "1.05rem", fontWeight: 500 } }}
      />

      <TextField
        fullWidth
        label="Description"
        value={data.description}
        onChange={(e) => update("description", e.target.value)}
        multiline
        rows={2}
        placeholder="A short description of your recipe..."
      />

      <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap", alignItems: "flex-end" }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
            Servings
          </Typography>
          <ServingsInput value={data.servings} onChange={(v) => update("servings", v)} />
        </Box>
        <TimeInput
          label="Prep Time"
          icon={<TimerIcon sx={{ fontSize: 13 }} />}
          value={data.prepTimeMinutes}
          onChange={(v) => update("prepTimeMinutes", v)}
        />
        <TimeInput
          label="Cook Time"
          icon={<ThermostatIcon sx={{ fontSize: 13 }} />}
          value={data.cookTimeMinutes}
          onChange={(v) => update("cookTimeMinutes", v)}
        />
      </Box>

      <Box>
        <Typography variant="caption" color="text.secondary">Difficulty</Typography>
        <Box sx={{ display: "flex", gap: 1, mt: 0.5 }}>
          {DIFFICULTIES.map((d) => (
            <Chip
              key={d.value}
              label={d.label}
              onClick={() => update("difficulty", d.value)}
              variant={data.difficulty === d.value ? "filled" : "outlined"}
              sx={{
                cursor: "pointer",
                fontWeight: data.difficulty === d.value ? 600 : 400,
                borderColor: data.difficulty === d.value ? d.color : "divider",
                bgcolor: data.difficulty === d.value ? `${d.color}18` : "transparent",
                color: data.difficulty === d.value ? d.color : "text.primary",
                "&:hover": { bgcolor: `${d.color}12` },
              }}
            />
          ))}
        </Box>
      </Box>

      <Box>
        <Typography variant="caption" color="text.secondary">Recipe Type</Typography>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 0.5 }}>
          {RECIPE_TYPES.map((t) => (
            <Chip
              key={t.value}
              label={t.label}
              onClick={() => update("recipeType", t.value)}
              variant={data.recipeType === t.value ? "filled" : "outlined"}
              color={data.recipeType === t.value ? "primary" : "default"}
              sx={{ cursor: "pointer" }}
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
};

// ─── Step 2: Ingredients ─────────────────────────────────────

const IngredientCard = ({ ingredient, index, onUpdate, onRemove }) => {
  const update = (field, value) => onUpdate(ingredient._id, field, value);

  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
        transition: "border-color 0.2s, box-shadow 0.2s",
        "&:hover": {
          borderColor: "primary.light",
          boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
        },
      }}
    >
      <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
        <Typography
          variant="caption"
          sx={{
            bgcolor: "primary.main",
            color: "white",
            borderRadius: 1,
            px: 0.7,
            py: 0.2,
            fontWeight: 700,
            fontSize: "0.65rem",
            mt: 1,
            flexShrink: 0,
            minWidth: 18,
            textAlign: "center",
          }}
        >
          {index + 1}
        </Typography>

        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", gap: 1 }}>
          <TextField
            fullWidth
            size="small"
            value={ingredient.name}
            onChange={(e) => update("name", e.target.value)}
            placeholder="Ingredient name"
            autoFocus={!ingredient.name}
            sx={{ "& .MuiInputBase-input": { fontWeight: 500 } }}
          />

          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <TextField
              size="small"
              type="number"
              value={ingredient.quantity}
              onChange={(e) => update("quantity", e.target.value)}
              placeholder="Qty"
              inputProps={{ min: 0, step: "any" }}
              sx={{ width: 76 }}
            />
            <FormControl size="small" sx={{ minWidth: 85 }}>
              <Select
                value={ingredient.unit}
                onChange={(e) => update("unit", e.target.value)}
                displayEmpty
              >
                {UNITS.map((u) => (
                  <MenuItem key={u.value} value={u.value}>{u.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 110, flex: 1 }}>
              <Select
                value={ingredient.category}
                onChange={(e) => update("category", e.target.value)}
              >
                {CATEGORIES.map((c) => (
                  <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
            <TextField
              size="small"
              fullWidth
              value={ingredient.preparation}
              onChange={(e) => update("preparation", e.target.value)}
              placeholder="Preparation (e.g. diced, melted...)"
              sx={{ "& .MuiInputBase-input": { fontSize: "0.85rem" } }}
            />
            <Tooltip title="Optional ingredient" arrow>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={ingredient.optional}
                    onChange={(e) => update("optional", e.target.checked)}
                  />
                }
                label={
                  <Typography variant="caption" color="text.secondary">Opt.</Typography>
                }
                sx={{ ml: 0, mr: 0, flexShrink: 0 }}
              />
            </Tooltip>
          </Box>
        </Box>

        <IconButton
          size="small"
          onClick={() => onRemove(ingredient._id)}
          sx={{ mt: 0.5, color: "text.disabled", "&:hover": { color: "error.main" } }}
        >
          <DeleteOutlineIcon fontSize="small" />
        </IconButton>
      </Box>
    </Paper>
  );
};

const IngredientsStep = ({ ingredients, onChange }) => {
  const addIngredient = () => onChange([...ingredients, createEmptyIngredient()]);
  const removeIngredient = (id) => onChange(ingredients.filter((i) => i._id !== id));
  const updateIngredient = (id, field, value) =>
    onChange(ingredients.map((i) => (i._id === id ? { ...i, [field]: value } : i)));

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Add the ingredients needed for your recipe.
      </Typography>

      {ingredients.length === 0 ? (
        <Paper
          elevation={0}
          onClick={addIngredient}
          sx={{
            p: 4,
            border: "2px dashed",
            borderColor: "divider",
            borderRadius: 2.5,
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.2s",
            "&:hover": { borderColor: "primary.light", bgcolor: "action.hover" },
          }}
        >
          <EggIcon sx={{ fontSize: 36, color: "text.disabled", mb: 0.5 }} />
          <Typography variant="body2" color="text.secondary">
            No ingredients added
          </Typography>
          <Typography variant="caption" color="text.disabled">
            Click to add your first ingredient
          </Typography>
        </Paper>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {ingredients.map((ingredient, index) => (
            <IngredientCard
              key={ingredient._id}
              ingredient={ingredient}
              index={index}
              onUpdate={updateIngredient}
              onRemove={removeIngredient}
            />
          ))}
        </Box>
      )}

      <Button
        startIcon={<AddIcon />}
        onClick={addIngredient}
        sx={{ mt: 2 }}
        variant="outlined"
        size="small"
      >
        Add Ingredient
      </Button>
    </Box>
  );
};

// ─── Step 3: Preparation ─────────────────────────────────────

const StepCard = ({ step, index, total, onUpdate, onRemove, onMove }) => {
  const update = (field, value) => onUpdate(step._id, field, value);

  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
        borderLeft: 3,
        borderLeftColor: "primary.main",
        transition: "box-shadow 0.2s",
        "&:hover": { boxShadow: "0 2px 8px rgba(0,0,0,0.05)" },
      }}
    >
      <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0.25, mt: 0.5 }}>
          <IconButton
            size="small"
            disabled={index === 0}
            onClick={() => onMove(index, index - 1)}
            sx={{ p: 0.25 }}
          >
            <ArrowUpIcon sx={{ fontSize: 15 }} />
          </IconButton>
          <Typography
            variant="caption"
            sx={{
              bgcolor: "primary.main",
              color: "white",
              borderRadius: "50%",
              width: 24,
              height: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: "0.72rem",
            }}
          >
            {index + 1}
          </Typography>
          <IconButton
            size="small"
            disabled={index === total - 1}
            onClick={() => onMove(index, index + 1)}
            sx={{ p: 0.25 }}
          >
            <ArrowDownIcon sx={{ fontSize: 15 }} />
          </IconButton>
        </Box>

        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", gap: 1 }}>
          <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
            {STEP_TYPES.map((st) => (
              <Chip
                key={st.value}
                label={st.label}
                size="small"
                onClick={() => update("stepType", st.value)}
                variant={step.stepType === st.value ? "filled" : "outlined"}
                color={step.stepType === st.value ? "primary" : "default"}
                sx={{ cursor: "pointer", height: 24, fontSize: "0.7rem" }}
              />
            ))}
          </Box>

          <TextField
            fullWidth
            multiline
            minRows={2}
            maxRows={5}
            size="small"
            value={step.action}
            onChange={(e) => update("action", e.target.value)}
            placeholder="Describe this preparation step..."
            autoFocus={!step.action}
          />

          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <TimerIcon sx={{ fontSize: 15, color: "text.secondary" }} />
              <TextField
                size="small"
                type="number"
                value={step.durationMinutes || ""}
                onChange={(e) => update("durationMinutes", parseInt(e.target.value) || 0)}
                placeholder="0"
                inputProps={{ min: 0, style: { textAlign: "center" } }}
                sx={{ width: 56 }}
              />
              <Typography variant="caption" color="text.secondary">min</Typography>
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <ThermostatIcon sx={{ fontSize: 15, color: "text.secondary" }} />
              <TextField
                size="small"
                type="number"
                value={step.temperature || ""}
                onChange={(e) => update("temperature", e.target.value)}
                placeholder="—"
                inputProps={{ min: 0, style: { textAlign: "center" } }}
                sx={{ width: 56 }}
              />
              <Typography variant="caption" color="text.secondary">°C</Typography>
            </Box>
          </Box>
        </Box>

        <IconButton
          size="small"
          onClick={() => onRemove(step._id)}
          sx={{ mt: 0.5, color: "text.disabled", "&:hover": { color: "error.main" } }}
        >
          <DeleteOutlineIcon fontSize="small" />
        </IconButton>
      </Box>
    </Paper>
  );
};

const PreparationStep = ({ steps, onChange }) => {
  const addStep = () => onChange([...steps, createEmptyStep()]);
  const removeStep = (id) => onChange(steps.filter((s) => s._id !== id));
  const updateStep = (id, field, value) =>
    onChange(steps.map((s) => (s._id === id ? { ...s, [field]: value } : s)));
  const moveStep = (from, to) => {
    const arr = [...steps];
    const [moved] = arr.splice(from, 1);
    arr.splice(to, 0, moved);
    onChange(arr);
  };

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Detail the preparation steps in order.
      </Typography>

      {steps.length === 0 ? (
        <Paper
          elevation={0}
          onClick={addStep}
          sx={{
            p: 4,
            border: "2px dashed",
            borderColor: "divider",
            borderRadius: 2.5,
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.2s",
            "&:hover": { borderColor: "primary.light", bgcolor: "action.hover" },
          }}
        >
          <RestaurantIcon sx={{ fontSize: 36, color: "text.disabled", mb: 0.5 }} />
          <Typography variant="body2" color="text.secondary">
            No steps added
          </Typography>
          <Typography variant="caption" color="text.disabled">
            Click to add your first step
          </Typography>
        </Paper>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {steps.map((step, index) => (
            <StepCard
              key={step._id}
              step={step}
              index={index}
              total={steps.length}
              onUpdate={updateStep}
              onRemove={removeStep}
              onMove={moveStep}
            />
          ))}
        </Box>
      )}

      <Button
        startIcon={<AddIcon />}
        onClick={addStep}
        sx={{ mt: 2 }}
        variant="outlined"
        size="small"
      >
        Add Step
      </Button>
    </Box>
  );
};

// ─── Step 4: Finalize ────────────────────────────────────────

const FinishStep = ({ data, onChange }) => {
  const update = (field, value) => onChange({ ...data, [field]: value });

  const addNote = () => update("notes", [...data.notes, ""]);
  const updateNote = (i, v) => {
    const n = [...data.notes];
    n[i] = v;
    update("notes", n);
  };
  const removeNote = (i) => update("notes", data.notes.filter((_, idx) => idx !== i));

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {/* Summary */}
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          bgcolor: "grey.50",
          borderRadius: 2.5,
          border: 1,
          borderColor: "divider",
        }}
      >
        <Typography variant="overline" color="text.secondary" sx={{ fontSize: "0.65rem", letterSpacing: 1.5 }}>
          Summary
        </Typography>
        <Typography variant="h6" sx={{ fontWeight: 700, mt: 0.5, mb: 0.5 }}>
          {data.title || "Untitled"}
        </Typography>
        {data.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            {data.description}
          </Typography>
        )}
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Chip size="small" icon={<RestaurantIcon />} label={`${data.servings} servings`} variant="outlined" />
          {data.prepTimeMinutes > 0 && (
            <Chip size="small" icon={<TimerIcon />} label={`Prep ${formatMinutes(data.prepTimeMinutes)}`} variant="outlined" />
          )}
          {data.cookTimeMinutes > 0 && (
            <Chip size="small" icon={<ThermostatIcon />} label={`Cook ${formatMinutes(data.cookTimeMinutes)}`} variant="outlined" />
          )}
          <Chip
            size="small"
            label={DIFFICULTIES.find((d) => d.value === data.difficulty)?.label}
            sx={{
              bgcolor: `${DIFFICULTIES.find((d) => d.value === data.difficulty)?.color}18`,
              color: DIFFICULTIES.find((d) => d.value === data.difficulty)?.color,
              fontWeight: 600,
            }}
          />
          <Chip size="small" label={RECIPE_TYPES.find((t) => t.value === data.recipeType)?.label} variant="outlined" />
        </Box>
        <Box sx={{ display: "flex", gap: 2, mt: 1.5 }}>
          <Typography variant="caption" color="text.secondary">
            {data.ingredients.length} ingredient{data.ingredients.length !== 1 ? "s" : ""}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {data.steps.length} step{data.steps.length !== 1 ? "s" : ""}
          </Typography>
        </Box>
      </Paper>

      {/* Tags */}
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Tags</Typography>
        <TagInput tags={data.tags} onChange={(v) => update("tags", v)} />
      </Box>

      {/* Notes */}
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Notes & Tips</Typography>
        {data.notes.map((note, index) => (
          <Box key={index} sx={{ display: "flex", gap: 1, mb: 1, alignItems: "flex-start" }}>
            <TextField
              fullWidth
              size="small"
              multiline
              value={note}
              onChange={(e) => updateNote(index, e.target.value)}
              placeholder="Add a note or tip..."
            />
            <IconButton
              size="small"
              onClick={() => removeNote(index)}
              sx={{ color: "text.disabled", "&:hover": { color: "error.main" } }}
            >
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          </Box>
        ))}
        <Button size="small" startIcon={<AddIcon />} onClick={addNote} variant="text">
          Add Note
        </Button>
      </Box>

      {/* Optional info */}
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Additional Information{" "}
          <Typography component="span" variant="caption" color="text.secondary">(optional)</Typography>
        </Typography>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <TextField
            size="small"
            label="Author"
            value={data.author}
            onChange={(e) => update("author", e.target.value)}
            sx={{ flex: 1, minWidth: 130 }}
          />
          <TextField
            size="small"
            label="Source"
            value={data.source}
            onChange={(e) => update("source", e.target.value)}
            placeholder="Book, website..."
            sx={{ flex: 1, minWidth: 130 }}
          />
          <TextField
            size="small"
            label="Nationality"
            value={data.nationality}
            onChange={(e) => update("nationality", e.target.value)}
            placeholder="French, Italian..."
            sx={{ flex: 1, minWidth: 130 }}
          />
        </Box>
      </Box>
    </Box>
  );
};

// ─── Main Wizard ─────────────────────────────────────────────

const ManualRecipeForm = ({ onSubmit, error, isSubmitting }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [formData, setFormData] = useState(INITIAL_FORM_DATA);
  const [validationError, setValidationError] = useState(null);

  const canProceed = useCallback(() => {
    switch (activeStep) {
      case 0: return formData.title.trim().length > 0;
      case 1: return formData.ingredients.length > 0 && formData.ingredients.every((i) => i.name.trim());
      case 2: return formData.steps.length > 0 && formData.steps.every((s) => s.action.trim());
      case 3: return true;
      default: return false;
    }
  }, [activeStep, formData]);

  const getStepError = () => {
    switch (activeStep) {
      case 0:
        if (!formData.title.trim()) return "Recipe name is required";
        return null;
      case 1:
        if (formData.ingredients.length === 0) return "Add at least one ingredient";
        if (formData.ingredients.some((i) => !i.name.trim())) return "All ingredients must have a name";
        return null;
      case 2:
        if (formData.steps.length === 0) return "Add at least one step";
        if (formData.steps.some((s) => !s.action.trim())) return "All steps must have a description";
        return null;
      default: return null;
    }
  };

  const handleNext = () => {
    const err = getStepError();
    if (err) { setValidationError(err); return; }
    setValidationError(null);
    setActiveStep((p) => p + 1);
  };

  const handleBack = () => {
    setValidationError(null);
    setActiveStep((p) => p - 1);
  };

  const handleStepClick = (idx) => {
    if (idx < activeStep) {
      setValidationError(null);
      setActiveStep(idx);
    }
  };

  const handleSubmit = () => {
    onSubmit({
      title: formData.title.trim(),
      description: formData.description.trim(),
      servings: formData.servings,
      prepTime: minutesToISO(formData.prepTimeMinutes),
      cookTime: minutesToISO(formData.cookTimeMinutes),
      difficulty: formData.difficulty,
      recipeType: formData.recipeType,
      ingredients: formData.ingredients.map((ing) => ({
        name: ing.name.trim(),
        quantity: ing.quantity ? parseFloat(ing.quantity) : null,
        unit: ing.unit || null,
        category: ing.category,
        preparation: ing.preparation.trim() || null,
        optional: ing.optional,
      })),
      steps: formData.steps.map((step) => ({
        action: step.action.trim(),
        stepType: step.stepType,
        duration: minutesToISO(step.durationMinutes),
        temperature: step.temperature ? parseInt(step.temperature) : null,
      })),
      tags: formData.tags,
      notes: formData.notes.filter((n) => n.trim()),
      author: formData.author.trim() || null,
      source: formData.source.trim() || null,
      nationality: formData.nationality.trim() || null,
    });
  };

  const updateFormData = (updates) => setFormData((p) => ({ ...p, ...updates }));

  return (
    <Box>
      <WizardStepper activeStep={activeStep} onStepClick={handleStepClick} />

      <Collapse in={!!validationError}>
        <Alert severity="warning" sx={{ mb: 2, borderRadius: 2 }} onClose={() => setValidationError(null)}>
          {validationError}
        </Alert>
      </Collapse>

      {error && (
        <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ minHeight: 280 }}>
        {activeStep === 0 && <BasicInfoStep data={formData} onChange={updateFormData} />}
        {activeStep === 1 && <IngredientsStep ingredients={formData.ingredients} onChange={(v) => updateFormData({ ingredients: v })} />}
        {activeStep === 2 && <PreparationStep steps={formData.steps} onChange={(v) => updateFormData({ steps: v })} />}
        {activeStep === 3 && <FinishStep data={formData} onChange={updateFormData} />}
      </Box>

      {/* Navigation */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          mt: 3,
          pt: 2,
          borderTop: 1,
          borderColor: "divider",
        }}
      >
        <Button
          startIcon={<BackIcon />}
          onClick={handleBack}
          disabled={activeStep === 0 || isSubmitting}
          sx={{ visibility: activeStep === 0 ? "hidden" : "visible" }}
        >
          Previous
        </Button>

        {activeStep === WIZARD_STEPS.length - 1 ? (
          <Button
            variant="contained"
            endIcon={<CheckIcon />}
            onClick={handleSubmit}
            disabled={!canProceed() || isSubmitting}
            disableElevation
            sx={{
              px: 3,
              py: 1,
              borderRadius: 2,
              fontWeight: 600,
              textTransform: "none",
              fontSize: "0.95rem",
            }}
          >
            {isSubmitting ? "Creating..." : "Create Recipe"}
          </Button>
        ) : (
          <Button
            variant="contained"
            endIcon={<NextIcon />}
            onClick={handleNext}
            disableElevation
            sx={{ px: 3, borderRadius: 2, textTransform: "none" }}
          >
            Next
          </Button>
        )}
      </Box>
    </Box>
  );
};

export default ManualRecipeForm;
