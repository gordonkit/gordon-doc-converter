import SwaggerUIBundle from "swagger-ui-dist/swagger-ui-es-bundle.js";
import "swagger-ui-dist/swagger-ui.css";
import "./styles.css";

SwaggerUIBundle({
  dom_id: "#swagger-ui",
  url: "../openapi.json",
  deepLinking: true,
  displayRequestDuration: true,
  docExpansion: "list",
  filter: true,
  supportedSubmitMethods: [],
});
