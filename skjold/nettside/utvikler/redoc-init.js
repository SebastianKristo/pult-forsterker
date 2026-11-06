// Starter Redoc på /utvikler/ og /en/developer/ (ingen inline-skript pga. CSP; søk av fordi Redoc-søket bruker blob-worker).
(function () {
  var el = document.getElementById("redoc");
  window.Redoc.init("/utvikler/openapi.yaml", {
    disableSearch: true, hideDownloadButton: false, expandResponses: "200", jsonSampleExpandLevel: 2, pathInMiddlePanel: true,
    theme: {
      colors: { primary: { main: "#d9a441" } },
      typography: { fontFamily: "'IBM Plex Sans', sans-serif", headings: { fontFamily: "Sora, sans-serif" }, code: { fontFamily: "'IBM Plex Mono', monospace" } },
      sidebar: { backgroundColor: "#111112", textColor: "#e8e8e3", activeTextColor: "#d9a441" },
      rightPanel: { backgroundColor: "#18181a" }
    }
  }, el);
})();
