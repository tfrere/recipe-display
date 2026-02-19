import React, { useState, useCallback } from "react";
import { Box, Button, Typography, IconButton } from "@mui/material";
import { useDropzone } from "react-dropzone";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import DeleteIcon from "@mui/icons-material/Delete";

const ImageRecipeForm = ({ onSubmit, error }) => {
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState("");

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
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
    if (!image) return;

    const reader = new FileReader();
    const imageBase64 = await new Promise((resolve) => {
      reader.onloadend = () => resolve(reader.result);
      reader.readAsDataURL(image);
    });

    await onSubmit({
      type: "image",
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
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Upload a photo of a recipe (cookbook page, handwritten recipe, screenshot…). 
        The text will be automatically extracted via OCR.
      </Typography>

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
          minHeight: "200px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <input {...getInputProps()} />

        {imagePreview ? (
          <Box sx={{ position: "relative" }}>
            <img
              src={imagePreview}
              alt="Recipe preview"
              style={{
                maxWidth: "100%",
                maxHeight: "300px",
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
            <PhotoCameraIcon sx={{ fontSize: 48, color: "grey.500", mb: 1 }} />
            <Typography variant="body1" color="text.secondary">
              {isDragActive
                ? "Drop the image here"
                : "Click or drop a recipe image here"}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              JPG, PNG or WebP
            </Typography>
          </Box>
        )}
      </Box>

      <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
        <Button
          onClick={handleSubmit}
          disabled={!image}
          variant="contained"
        >
          Extract & Add
        </Button>
      </Box>
    </Box>
  );
};

export default ImageRecipeForm;
