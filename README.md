# 📡 ADG Licitaciones

**Observatorio de licitaciones públicas de diseño gráfico y comunicación visual en España.**

Herramienta que recopila, filtra y clasifica automáticamente los contratos públicos relevantes para el sector del diseño desde la [Plataforma de Contratación del Sector Público](https://contrataciondelestado.es), facilitando su seguimiento a profesionales, estudios y asociaciones.

> Proyecto impulsado por la **ADG · Associació de Disseny Gràfic i Comunicació Visual** y desarrollado por [Collapse Creative](https://collapsecreative.com).

---

## ✨ Características

- 🔍 **Filtros avanzados** — por disciplina (multi-selección OR), CCAA, provincia, estado, año y texto libre
- 🏷️ **10 disciplinas** — Branding, Editorial, Web, UX·UI, Publicidad, Señalética, Fotografía, Audiovisual, Ilustración, Impresión
- 🚦 **Semáforo de estados** — Vigente (verde), Adjudicado (gris), Desierta (rojo)
- 📊 **Panel de estadísticas** — bignums, donut de estados, evolución mensual, rankings por presupuesto, organismo, territorio y disciplina, condiciones del mercado — con filtros locales independientes
- 📖 **Guía de licitaciones** — señales de alerta, buenas señales, marco legal LCSP 9/2017 y recursos útiles
- 🌍 **4 idiomas** — Castellano, Catalán, Euskera y Gallego (con persistencia)
- 🌙 **Tema claro / oscuro** — con paleta de colores por disciplina en ambos modos
- 🔔 **Alertas por email** — suscripción por disciplina y territorio (Formspree)
- 📥 **Exportación CSV** — descarga de resultados filtrados
- 🔗 **Compartir licitación** — URL con query param para enlace directo
- 🤖 **Actualización diaria** — GitHub Actions + feeds ATOM de PLACSP

---

## 🗂️ Estructura

```
index.html              Tabla principal con filtros y panel de detalle
index.js                Lógica: filtrado multi-disc, ordenación, paginación, CSV, detalle
estadisticas.html       Panel de estadísticas forense
estadisticas.js         Filtros locales independientes, bignums, donut, barCards, tops
about.html              Acerca de (2 columnas) + guía de licitaciones
about.js                Changelog del proyecto
style.css               CSS compartido: tokens, layout, tabla, stats, modales, about, guía
app.js                  Módulo compartido: DISC, TERR, I18N, SAMPLE, estado, utils
fetch_licitaciones.py   Fetcher v2.0 (descarga ATOM/ZIP + scoring + enriquecimiento)
data.json               Generado por el fetcher (no versionado)
fonts/
  └── NeueHaasUnica.otf
img/
  ├── img_1.png
  └── img_2.png
.github/
  └── workflows/
      └── fetch.yml     Actualización diaria automática
```

---

## ⚙️ Cómo funciona

**Fetcher** → El script `fetch_licitaciones.py` descarga licitaciones desde dos feeds ATOM de PLACSP, las puntúa por relevancia para el sector del diseño (palabras clave + códigos CPV), enriquece los datos, y genera `data.json`. Solo se incluyen licitaciones con puntuación ≥ 20.

**Frontend** → Tres páginas estáticas que consumen `data.json`. Sin framework, sin build, sin backend — vanilla HTML/CSS/JS. Si `data.json` no existe, la app muestra 10 licitaciones de ejemplo como fallback.

**Automatización** → GitHub Actions ejecuta el fetcher cada noche a las 03:00 UTC. Si hay cambios, commitea el nuevo `data.json` automáticamente.

---

## 💻 Uso local

Abre `index.html` directamente o lanza un servidor local:

```bash
python -m http.server 8000
```

Para ejecutar el fetcher:

```bash
# Desde feeds ATOM en vivo
python fetch_licitaciones.py --min-score 20

# Desde ZIPs descargados en local
python fetch_licitaciones.py --local-dir "./historico" --min-score 20
```

---

## 🛠️ Stack

- **Frontend** — HTML, CSS, JavaScript vanilla (zero dependencies)
- **Iconos** — Bootstrap Icons (CDN)
- **Tipografía** — Neue Haas Unica
- **Fetcher** — Python 3.12 (requests)
- **CI/CD** — GitHub Actions

---

## 📋 Fuentes de datos

| Feed | URL |
|------|-----|
| PLACSP-643 | contrataciondelestado.es/sindicacion/sindicacion_643/ |
| PLACSP-1044 | contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_1044/ |

Los datos son siempre información pública. No se realiza scraping de pantallas ni se vulneran términos de servicio.

---

<p align="center">
  Hecho con ☕ por <a href="https://collapsecreative.com">Collapse Creative</a> para la <a href="https://adg-fad.org">ADG-FAD</a>
</p>
