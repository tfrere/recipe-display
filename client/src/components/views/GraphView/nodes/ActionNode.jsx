const ActionNode = ({ data }) => {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #ddd",
        borderRadius: "4px",
        padding: "10px",
        width: "120px",
        height: "180px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "8px",
        fontSize: "12px",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
      }}
    >
      <div
        style={{ fontWeight: "bold", textAlign: "center", marginBottom: "4px" }}
      >
        {data.label}
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "4px",
          justifyContent: "center",
          marginBottom: "4px",
        }}
      >
        {data.tools &&
          data.tools.map((tool, index) => (
            <span
              key={index}
              style={{
                background: "#f0f0f0",
                padding: "2px 6px",
                borderRadius: "12px",
                fontSize: "10px",
              }}
            >
              {tool}
            </span>
          ))}
      </div>

      {data.ingredients && (
        <div
          style={{
            fontSize: "11px",
            textAlign: "center",
            color: "#666",
            marginTop: "auto",
          }}
        >
          {data.ingredients.map((ing, index) => (
            <div key={index}>{ing}</div>
          ))}
        </div>
      )}
    </div>
  );
};
