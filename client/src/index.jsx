import React, { Suspense } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <Suspense fallback="Loading...">
    <App />
  </Suspense>
);
