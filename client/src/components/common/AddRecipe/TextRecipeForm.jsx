import React, { useState, useCallback } from "react";
import { Box, TextField, Button, Typography, IconButton } from "@mui/material";
import { useDropzone } from "react-dropzone";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DeleteIcon from "@mui/icons-material/Delete";

const TextRecipeForm = ({ onSubmit, error }) => {
  const [recipeText, setRecipeText] = useState("");
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState("");

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);

      // Store file for submission
      setImage(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".jpeg", ".jpg", ".png", ".webp"],
    },
    maxFiles: 1,
  });

  const handleSubmit = async () => {
    let imageBase64 = null;
    if (image) {
      const reader = new FileReader();
      imageBase64 = await new Promise((resolve) => {
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(image);
      });
    }

    await onSubmit({
      type: "text",
      text: recipeText,
      image: imageBase64,
    });
  };

  const handleRemoveImage = (e) => {
    e.stopPropagation();
    setImage(null);
    setImagePreview("");
  };

  return (
    <Box>
      <TextField
        fullWidth
        multiline
        rows={6}
        label="Texte de la recette"
        value={recipeText}
        onChange={(e) => setRecipeText(e.target.value)}
        error={!!error}
        helperText={error}
        sx={{ mb: 3 }}
      />

      <Box
        {...getRootProps()}
        sx={{
          border: "2px dashed",
          borderColor: isDragActive ? "primary.main" : "grey.300",
          borderRadius: 1,
          p: 3,
          mb: 2,
          textAlign: "center",
          cursor: "pointer",
          position: "relative",
        }}
      >
        <input {...getInputProps()} />

        {imagePreview ? (
          <Box sx={{ position: "relative" }}>
            <img
              src={imagePreview}
              alt="Preview"
              style={{
                maxWidth: "100%",
                maxHeight: "200px",
                objectFit: "contain",
              }}
            />
            <IconButton
              onClick={handleRemoveImage}
              sx={{
                position: "absolute",
                top: -12,
                right: -12,
                bgcolor: "background.paper",
              }}
              size="small"
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        ) : (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 48, color: "grey.500", mb: 1 }} />
            <Typography variant="body1" color="text.secondary">
              {isDragActive
                ? "Déposez l'image ici"
                : "Cliquez ou déposez une image ici"}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              JPG, PNG ou WebP
            </Typography>
          </Box>
        )}
      </Box>

      <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
        <Button
          onClick={handleSubmit}
          disabled={!recipeText}
          variant="contained"
        >
          Ajouter
        </Button>
      </Box>
    </Box>
  );
};

export default TextRecipeForm;
