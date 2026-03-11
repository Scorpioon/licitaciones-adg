# 📡 ADG Licitaciones

**Observatorio de licitaciones públicas de diseño gráfico y comunicación visual en España.**

Herramienta que recopila, filtra y clasifica automáticamente los contratos públicos relevantes para el sector del diseño desde la [Plataforma de Contratación del Sector Público](https://contrataciondelestado.es), facilitando su seguimiento a profesionales, estudios y asociaciones.

> Proyecto impulsado por la **Asociación de Diseño Gráfico y Comunicación Visual (ADG)**.

---

## ✨ Características

- 🔍 **Búsqueda y filtros avanzados** — por disciplina, comunidad autónoma, estado, presupuesto y texto libre
- 🏷️ **Multi-disciplina** — selección múltiple con lógica OR y chips removibles
- 📊 **Panel de estadísticas** — bignums, donuts, barras y rankings con filtros independientes
- 🌍 **4 idiomas** — Castellano, Catalán, Euskera y Gallego
- 🌙 **Tema claro / oscuro** — con paleta de colores por disciplina
- 🤖 **Actualización diaria automática** — GitHub Actions + feeds ATOM de PLACSP
- 📥 **Exportación CSV** — descarga de resultados filtrados
- 📖 **Guía de licitaciones** — sección didáctica para quienes empiezan

---

## 🗂️ Estructura del proyecto

```
├── index.html              Tabla principal con filtros
├── index.js                Lógica de tabla, filtros, detalle y paginación
├── estadisticas.html       Panel de estadísticas
├── estadisticas.js         Filtros locales, bignums, donut, barCards, tops
├── about.html              Acerca de + guía de licitaciones
├── about.js                Changelog vivo desde GitHub Commits API
├── style.css               CSS compartido (tokens, layout, tabla, stats, modales)
├── app.js                  Módulo compartido (colores, territorios, i18n, utils)
├── fetch_licitaciones.py   Fetcher v2.0 (descarga + scoring + enriquecimiento)
├── data.json               Datos generados por el fetcher
├── fonts/
│   └── NeueHaasUnica.otf
├── img/
│   ├── img_1.png
│   └── img_2.png
└── .github/
    └── workflows/
        └── fetch.yml       Workflow de actualización diaria
```

---

## 🚀 Cómo funciona

### Datos

El fetcher (`fetch_licitaciones.py`) descarga las licitaciones desde dos feeds ATOM de la Plataforma de Contratación del Sector Público:

| Feed | Fuente |
|------|--------|
| `PLACSP-643` | contrataciondelestado.es |
| `PLACSP-1044` | contrataciondelsectorpublico.gob.es |

Cada licitación se puntúa por relevancia para el sector del diseño gráfico y comunicación visual. Solo se incluyen aquellas con una puntuación ≥ 20. El resultado se escribe en `data.json`.

### Automatización

GitHub Actions ejecuta el fetcher cada noche a las 03:00 UTC. Si hay cambios, commitea el nuevo `data.json` automáticamente. También se puede lanzar manualmente desde la pestaña **Actions** del repositorio.

### Frontend

Tres páginas estáticas (`index`, `estadisticas`, `about`) que consumen `data.json`. No requiere backend, frameworks ni build — basta con servir los ficheros. Si `data.json` no está disponible, la app muestra datos de ejemplo como fallback.

---

## 💻 Uso local

Abre `index.html` en el navegador o lanza un servidor local:

```bash
python -m http.server 8000
```

Para ejecutar el fetcher manualmente:

```bash
# Desde feeds ATOM en vivo
python fetch_licitaciones.py --min-score 20

# Desde ZIPs descargados localmente
python fetch_licitaciones.py --local-dir "./historico" --min-score 20
```

---

## 🛠️ Tecnologías

- **Frontend** — HTML, CSS y JavaScript vanilla (sin dependencias externas)
- **Fetcher** — Python 3.12 (requests, feedparser, lxml)
- **CI/CD** — GitHub Actions
- **Tipografía** — Neue Haas Unica

---

## 📄 Licencia

Este proyecto es de código abierto. Consulta el fichero `LICENSE` para más detalles.

---

<p align="center">
  Hecho con ☕ para la comunidad del diseño en España
</p>
