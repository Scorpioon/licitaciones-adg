# ADG Plataforma Digital

Plataforma digital open source para la comunidad del diseño gráfico y la comunicación visual.

Reúne en un mismo ecosistema:

- observatorio de licitaciones públicas
- estadísticas y análisis del mercado
- recursos profesionales y calculadora de honorarios
- mapa territorial de actividad
- barómetro automático del sector
- documentación metodológica del proyecto

Proyecto impulsado por la **ADG · Associació de Disseny Gràfic i Comunicació Visual** y desarrollado por **Collapse Creative**.

---

## Qué es

ADG Plataforma Digital es una herramienta estática, modular y abierta que traduce datos públicos de contratación en una interfaz útil para:

- diseñadores y freelancers
- estudios y agencias
- asociaciones profesionales
- estudiantes y escuelas
- investigación y observación del sector

El núcleo actual del proyecto es el **Observatorio de Licitaciones**, que recopila y filtra contratos públicos relacionados con diseño gráfico y comunicación visual en España.

---

## Módulos actuales

### 1. Inicio
Hub central del ecosistema. Presenta todas las herramientas activas y futuras desde una única portada.

### 2. Licitaciones
Observatorio principal con:

- filtros por disciplina, CCAA, provincia/comarca, estado, año y texto libre
- búsqueda por adjudicatario
- paginación
- exportación CSV
- detalle lateral por licitación
- histórico de estados
- compartir por URL

### 3. Estadísticas
Panel analítico independiente con filtros locales propios para explorar:

- volumen
- disciplinas
- territorios
- evolución temporal
- tops y rankings
- condiciones del mercado

### 4. Recursos + Calculadora
Módulo orientado a práctica profesional:

- calculadora de honorarios
- referencias y recursos
- materiales de apoyo legal y operativo

### 5. Mapa
Mapa territorial del ecosistema de licitaciones con visualización por CCAA y filtros por disciplina / estado.

### 6. Barómetro del Sector
Informe automático imprimible generado a partir del dataset actual.

### 7. Acerca de
Explica metodología, fuentes, changelog y guía básica para leer y usar la herramienta.

---

## Stack

- **Frontend:** HTML, CSS y JavaScript vanilla
- **Datos:** JSON estático
- **Fetcher:** Python + `requests`
- **Mapas:** Leaflet
- **Iconos:** Bootstrap Icons
- **Deploy:** GitHub Pages
- **Automatización:** GitHub Actions

Sin framework, sin build step, sin backend persistente.

---

## Arquitectura actual

```txt
index.html            Hub principal / portada
licitaciones.html     Observatorio de licitaciones
estadisticas.html     Panel analítico
recursos.html         Recursos + calculadora
mapa.html             Mapa territorial
barometro.html        Informe automático
about.html            Metodología + changelog + guía

app.js                Estado compartido, i18n, utils, carga de datos
style.css             Estilos compartidos
licitaciones.js       Lógica de tabla principal
estadisticas.js       Lógica del dashboard
recursos.js           Calculadora + recursos
mapa.js               Lógica del mapa
barometro.js          Generación del informe
about.js              Changelog y capa editorial

fetch_licitaciones.py Fetcher y pipeline de datos

data/
  licitaciones.json   Dataset consumido por el frontend
  recursos.json       Datos del módulo de recursos/calculadora
