// Theme toggle: explicit choice wins over OS preference either direction,
// persisted so it sticks across pages (see dataviz skill: dark mode is
// "selected," not an automatic flip).
(function () {
  const stored = localStorage.getItem("theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);

  document.addEventListener("DOMContentLoaded", function () {
    const button = document.querySelector(".theme-toggle");
    if (!button) return;
    button.addEventListener("click", function () {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
    });
  });
})();

// Click-to-sort for any table.data-table -- numeric columns sort as numbers
// (detected from the first data row), everything else sorts as text.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("table.data-table").forEach(function (table) {
    const headers = table.querySelectorAll("thead th");
    headers.forEach(function (th, colIndex) {
      th.addEventListener("click", function () {
        const tbody = table.querySelector("tbody");
        const rows = Array.from(tbody.querySelectorAll("tr"));
        const ascending = th.dataset.sortDir !== "asc";
        headers.forEach((h) => delete h.dataset.sortDir);
        th.dataset.sortDir = ascending ? "asc" : "desc";

        rows.sort(function (a, b) {
          const aText = a.children[colIndex].textContent.trim();
          const bText = b.children[colIndex].textContent.trim();
          const aNum = parseFloat(aText.replace(/[%,]/g, ""));
          const bNum = parseFloat(bText.replace(/[%,]/g, ""));
          const bothNumeric = !isNaN(aNum) && !isNaN(bNum);
          const cmp = bothNumeric ? aNum - bNum : aText.localeCompare(bText);
          return ascending ? cmp : -cmp;
        });

        rows.forEach((row) => tbody.appendChild(row));
      });
    });
  });
});
