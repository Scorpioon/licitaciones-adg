/* ADG Plataforma Digital — laus.js | 0.1.3.1 May 2026 | Phase 2R-4A */
/* Renderer / adapter only. No data arrays. Fetches local JSON. */
(function () {
  "use strict";

  var DATA_BASE = "./data/public/laus/";

  document.addEventListener("DOMContentLoaded", function () {
    Promise.all([
      fetch(DATA_BASE + "editions.json").then(function (r) { return r.json(); }),
      fetch(DATA_BASE + "juries.json").then(function (r) { return r.json(); }),
      fetch(DATA_BASE + "categories.json").then(function (r) { return r.json(); })
    ])
      .then(function (results) {
        var editions   = results[0];
        var juries     = results[1];
        var categories = results[2];

        var years = editions
          .map(function (e) { return e.year; })
          .sort(function (a, b) { return b - a; });

        var activeYear = years[0];

        renderYearSelector(years, activeYear, editions, juries, categories);
        renderAll(activeYear, editions, juries, categories);
      })
      .catch(function (err) {
        console.error("Laus Tracker — fetch error:", err);
        showError();
      });
  });

  function renderYearSelector(years, activeYear, editions, juries, categories) {
    var container = document.getElementById("laus-year-selector");
    if (!container) return;
    container.innerHTML = "";
    years.forEach(function (year) {
      var btn = document.createElement("button");
      btn.textContent = year;
      btn.className = "laus-year-btn" + (year === activeYear ? " laus-year-btn--active" : "");
      btn.setAttribute("aria-pressed", year === activeYear ? "true" : "false");
      btn.addEventListener("click", function () {
        container.querySelectorAll(".laus-year-btn").forEach(function (b) {
          b.classList.remove("laus-year-btn--active");
          b.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("laus-year-btn--active");
        btn.setAttribute("aria-pressed", "true");
        renderAll(year, editions, juries, categories);
      });
      container.appendChild(btn);
    });
  }

  function renderAll(year, editions, juries, categories) {
    var edition = editions.find(function (e) { return e.year === year; });
    var yearJuries = juries.filter(function (j) { return j.year === year; });
    var yearCats   = categories.filter(function (c) { return c.year === year; });
    renderStats(edition);
    renderCategories(yearCats);
    renderJury(yearJuries, year);
  }

  function renderStats(edition) {
    var container = document.getElementById("laus-stats");
    if (!container) return;
    if (!edition) {
      container.innerHTML = '<p class="laus-no-data">Edición no encontrada.</p>';
      return;
    }
    var note = edition.status_note
      ? '<p class="laus-status-note">' + escHtml(edition.status_note) + "</p>"
      : "";
    container.setAttribute("data-source", "adg-public");
    container.innerHTML =
      '<h2 class="laus-edition-title">' + escHtml(edition.edition_label) + "</h2>" +
      note +
      '<div class="laus-stats-grid">' +
        statCell("Participantes", edition.participants) +
        statCell("Nacionalidades", edition.nationalities) +
        statCell("Premios otorgados", edition.awards_count) +
        statCell("Asistentes Nit Laus", edition.attendees_nit_laus) +
      "</div>";
  }

  function statCell(label, value) {
    var display = value !== null && value !== undefined ? value : "—";
    return (
      '<div class="laus-stat-cell">' +
        '<span class="laus-stat-value">' + display + "</span>" +
        '<span class="laus-stat-label">' + escHtml(label) + "</span>" +
      "</div>"
    );
  }

  function renderCategories(yearCats) {
    var container = document.getElementById("laus-categories");
    if (!container) return;
    if (!yearCats.length) {
      container.innerHTML = '<p class="laus-no-data">No hay categorías registradas para esta edición.</p>';
      return;
    }
    container.innerHTML =
      '<h3 class="laus-section-title">Categorías</h3>' +
      '<ul class="laus-cat-list">' +
      yearCats.map(function (c) {
        return '<li class="laus-cat-item">' + escHtml(c.label) + "</li>";
      }).join("") +
      "</ul>";
  }

  function renderJury(yearJuries, year) {
    var container = document.getElementById("laus-jury");
    if (!container) return;
    container.setAttribute("data-source", "adg-public");

    var grouped = {};
    yearJuries.forEach(function (j) {
      var cat = j.category_judged || "Sin categoría asignada";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(j);
    });

    var catKeys = Object.keys(grouped);
    if (!catKeys.length) {
      container.innerHTML =
        '<h3 class="laus-section-title">Jurado ' + year + "</h3>" +
        '<p class="laus-no-data">No hay datos de jurado para esta edición.</p>';
      return;
    }

    var html = '<h3 class="laus-section-title">Jurado ' + year + "</h3>";
    html += '<p class="laus-seed-notice">Datos de jurado — muestra representativa (fuente pública). Importación completa: Fase 2R-4B.</p>';

    catKeys.forEach(function (cat) {
      html += '<div class="laus-jury-group">';
      html += '<h4 class="laus-jury-cat-title">' + escHtml(cat) + "</h4>";
      html += '<ul class="laus-jury-list">';
      grouped[cat].forEach(function (j) {
        var chair = j.is_chair === true
          ? ' <span class="laus-chair-badge">Presidente/a</span>'
          : "";
        var studio = j.studio_or_context
          ? ' <span class="laus-jury-studio">— ' + escHtml(j.studio_or_context) + "</span>"
          : "";
        html +=
          '<li class="laus-jury-item">' +
            '<span class="laus-jury-name">' + escHtml(j.name) + "</span>" + chair +
            '<span class="laus-jury-role">' + escHtml(j.role || "") + studio + "</span>" +
          "</li>";
      });
      html += "</ul></div>";
    });

    container.innerHTML = html;
  }

  function showError() {
    var ids = ["laus-stats", "laus-categories", "laus-jury"];
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) {
        el.innerHTML =
          '<p class="laus-error">Error cargando datos. Asegúrate de servir la página desde un servidor local (<code>python -m http.server</code>).</p>';
      }
    });
  }

  function escHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();
