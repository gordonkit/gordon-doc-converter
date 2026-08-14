declare module "swagger-ui-dist/swagger-ui-es-bundle.js" {
  type SwaggerUIOptions = {
    dom_id: string;
    url: string;
    deepLinking?: boolean;
    displayRequestDuration?: boolean;
    docExpansion?: "list" | "full" | "none";
    filter?: boolean;
    supportedSubmitMethods?: string[];
  };

  const SwaggerUIBundle: (options: SwaggerUIOptions) => unknown;
  export default SwaggerUIBundle;
}
