(() => {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("gordon-docs-theme");
  const preferredTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  root.dataset.theme = savedTheme || preferredTheme;

  const button = document.querySelector("[data-theme-toggle]");
  if (!button) return;
  button.addEventListener("click", () => {
    const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = nextTheme;
    localStorage.setItem("gordon-docs-theme", nextTheme);
    button.setAttribute("aria-label", nextTheme === "dark" ? "Use light theme" : "Use dark theme");
  });
})();
