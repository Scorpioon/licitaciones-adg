# 📡 ADG Licitaciones v0.6.90

**Observatorio de licitaciones públicas de diseño gráfico y comunicación visual en España** — más un conjunto de herramientas digitales para la comunidad de la ADG-FAD.

Recopila, filtra y clasifica automáticamente los contratos públicos relevantes para el sector del diseño desde la [Plataforma de Contratación del Sector Público](https://contrataciondelestado.es), y los pone a disposición junto con recursos, mapa territorial, registro de premios Laus, directorio de socios y otras superficies públicas.

> Proyecto impulsado por la **ADG · Associació de Disseny Gràfic i Comunicació Visual** y desarrollado por [Collapse Creative](https://collapsecreative.com).

---

## ✨ Superficies

- 🏠 **Inicio** — hub central con acceso a todas las herramientas
- 🔍 **Licitaciones** — observatorio principal: filtros por disciplina (multi-selección OR), CCAA, provincia, estado, año y texto libre; panel de detalle; exportación CSV; compartir por URL
- 📊 **Estadísticas** — bignums, evolución mensual, rankings por presupuesto/organismo/territorio/disciplina, barómetro del sector
- 🧰 **Recursos** — calculadora de honorarios profesionales y recursos legales (contratos, tarifas, derechos de autor)
- 🗺️ **Mapa** — mapa interactivo (Leaflet) con licitaciones vigentes geolocalizadas por CCAA
- 🏆 **Laus** — registro de referencia de los premios ADG Laus (ediciones, categorías, jurados) según datos públicos disponibles
- 🗂️ **Directorio** — listado de socios según fuente pública de adg-fad.org/socios; solo nombres, sin datos de contacto ni perfiles
- 💼 **Oportunidades** — página informativa, shell estático "próximamente"; sin formularios, sin registro, sin captura de datos
- 🔔 **Alertas** — página stub "en estudio"; sin captura de datos, sin suscripción por email activa
- ℹ️ **Acerca de** — changelog público, guía de licitaciones y crédito del proyecto

**Idiomas** — Castellano, Catalán, Euskera y Gallego, con persistencia. **Tema** — claro / oscuro con paleta de colores por disciplina.

---

## ⚙️ Cómo funciona

**Fetcher 1** → workflow programado (GitHub Actions) que descarga licitaciones desde los feeds ATOM de PLACSP, las puntúa por relevancia para el sector del diseño (palabras clave + códigos CPV) y actualiza el dataset público de forma incremental. Tras cada actualización, los shards JSON públicos (`data/licitaciones_*.json` + manifest) se regeneran y validan para que la web cargue siempre datos consistentes. No hay captura de datos personales en este flujo.

**Frontend** → páginas estáticas que consumen los shards de `data/`. Sin framework, sin build, sin backend — vanilla HTML/CSS/JS. Cada página de contenido (`licitaciones.html`, `estadisticas.html`, etc.) tiene su propio script; `app.js` y `shared.js` son módulos compartidos (estado, I18N, utilidades, componentes UI) cargados por todas las páginas.

**Automatización** → GitHub Actions ejecuta el fetcher varias veces al día. Si hay cambios, el workflow commitea el nuevo dataset y sus shards automáticamente.

---

## 🛠️ Stack

- **Frontend** — HTML, CSS, JavaScript vanilla (zero dependencies de runtime)
- **Iconos** — Bootstrap Icons (CDN)
- **Mapa** — Leaflet (CDN)
- **Tipografía** — Neue Haas Unica
- **Fetcher** — Python 3.12
- **CI/CD** — GitHub Actions

---

## 📋 Fuentes de datos

| Feed | URL |
|------|-----|
| PLACSP-643 | contrataciondelestado.es/sindicacion/sindicacion_643/ |
| PLACSP-1044 | contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_1044/ |
| Laus | datos públicos de ediciones históricas de los premios ADG Laus |
| Directorio | adg-fad.org/socios (solo nombres) |

Los datos son siempre información pública. No se realiza scraping de pantallas ni se vulneran términos de servicio.

---

<p align="center">
  Hecho con ☕ por <a href="https://collapsecreative.com">Collapse Creative</a> para la <a href="https://adg-fad.org">ADG-FAD</a>
</p>
