import { Checkbox } from "@mui/material";

const CustomNode = ({ data }) => {
  const { type, label, quantity, isCompleted, onClick, isUnused } = data;

  const getNodeStyle = () => {
    const baseStyle = {
      padding: "10px",
      borderRadius: "8px",
      textAlign: "center",
      cursor: type === "action" ? "pointer" : "default",
      opacity: isUnused ? 0.5 : 1,
    };

    switch (type) {
      case "action":
        return {
          ...baseStyle,
          backgroundColor: isCompleted ? "#e0e0e0" : "#ffffff",
          border: "1px solid #ccc",
          width: "150px",
        };
      case "ingredient":
        return {
          ...baseStyle,
          backgroundColor: "#e3f2fd",
          border: "1px solid #90caf9",
          width: "120px",
        };
      case "tool":
        return {
          ...baseStyle,
          backgroundColor: "#f3e5f5",
          border: "1px solid #ce93d8",
          width: "120px",
        };
      default:
        return baseStyle;
    }
  };

  return (
    <div style={getNodeStyle()} onClick={onClick}>
      <div style={{ marginBottom: "5px" }}>{label}</div>
      {quantity && <div style={{ fontSize: "0.8em" }}>{quantity}</div>}
      {type === "action" && (
        <Checkbox
          checked={isCompleted}
          onChange={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
          size="small"
          style={{ padding: 0, marginTop: "5px" }}
        />
      )}
    </div>
  );
};

export default CustomNode;
