# ADGOPS_002_SUITE_MAP_v2.0

Status: ACTIVE DRAFT  
Authority: ADG OPS suite structure map  
Parent docs: `ADGOPS_000_DOC_ARCHITECTURE_v2.0`, `ADGOPS_001_STATUS_QUO_v2.0`  
Language: English  
Purpose: Define ADG OPS as a suite, identify its major current surfaces, and position future additions without pretending they already exist.

---

## 0. What this document is

This is the suite map for ADG OPS.

It exists to answer:
- what ADG OPS is as a system
- which major surfaces currently belong to it
- how those surfaces relate
- which areas are currently core
- which areas are supportive
- which future additions are already strategically relevant

This is not:
- the full runtime truth doc
- the intended direction doc
- the per-surface documentation set
- the roadmap
- a code architecture diagram

One-line doctrine:

**ADG OPS should be read as a modular suite with surface identity, not as a single monolithic page.**

---

## 1. Suite definition

ADG OPS is currently understood as:

- a modular public-sector / sector-intelligence suite
- surface-first in user experience
- centered on licitaciones as a technical and conceptual core
- expanded by analytics, interpretation, navigation, resources, alerts, and future ecosystem capabilities

The suite is open to future additions.
This openness is intentional, not accidental.

Important:
- future openness does not mean infinite scope now
- current docs must still describe what exists today first

---

## 2. Current surface families

## 2.1 Core operational surfaces

### Licitaciones
Role:
- core technical and conceptual surface
- primary working reality from which much of the rest of the suite draws

Meaning:
- licitaciones is not just another page
- it is one of the deepest product cores and deserves deeper documentation

### Estadisticas
Role:
- configurable analytics surface
- allows reading and filtering statistical views of the sector by different dimensions

### Barometro
Role:
- sibling analytics surface with its own identity
- focused on period-based sector reading
- analyzes the state of the sector by quadrimester / period
- extracts and frames an automatic reading of public procurement behavior over the selected time frame

Important:
- `barometro` shares UI space with `estadisticas`
- but functionally it is not the same thing
- it should be treated as its own documentation unit

---

## 2.2 Supporting / contextual surfaces

### Mapa
Role:
- spatial / mapping-related reading of the ecosystem

### Recursos
Role:
- supporting resource surface

### Alertas
Role:
- current alert-related surface
- strategically important because future alerting capabilities likely expand the suite meaningfully

### Index
Role:
- entry surface
- suite gateway
- light doc at first, but still part of the documented system

### About
Role:
- explanation / framing surface
- light doc at first, but still part of the suite map

---

## 3. Surface hierarchy reading

Preferred reading:

### Level 1 — Core suite identity
- Licitaciones
- Estadisticas
- Barometro

### Level 2 — Supporting intelligence / context surfaces
- Mapa
- Recursos
- Alertas

### Level 3 — Entry / framing surfaces
- Index
- About

This hierarchy is descriptive, not a statement of product importance forever.
It reflects current documentation priority and current product reading.

---

## 4. Current strategic center

The current strategic center of ADG OPS appears to be:

- licitaciones as the technical/conceptual base
- estadisticas as configurable analytical reading
- barometro as interpretive period-based sector analysis

This triangle is the current highest-value documentation cluster.

That is why:
- `licitaciones` deserves a deep doc
- `barometro` deserves a deep doc
- `estadisticas` deserves a full surface doc even if it shares UI space

---

## 5. Future suite additions already in orbit

The following additions are already strategically relevant enough to belong in the suite reading, even if they are not fully implemented:

- database / SQL-backed data evolution
- Laus Tracker
- partner directory
- internship board
- email alerts
- future multi-fetcher data intake architecture

These should be treated as:
- future ecosystem capabilities
- not current stable modules

They belong more fully in:
- `ADGOPS_005_INTENDED_DIRECTION_v2.0`
- `ADGOPS_006_FUTURE_MODULES_v2.0`
- `ADGOPS_007_DATA_AND_FETCHING_v2.0`

---

## 6. What belongs to current truth vs intended truth

## Current truth
Current truth includes:
- the real current surfaces
- the current development repo
- current working and broken areas
- active but incomplete tooling like the fetcher
- partial runtime behavior

## Intended truth
Intended truth includes:
- broader data infrastructure
- multiple fetchers
- SQL / DB learning and integration
- future ecosystem modules
- expanded services like alerts and directories

Rule:
- the suite map may mention future additions
- but it must not present them as if they are current stable modules

---

## 7. Documentation consequences

Because ADG OPS is a suite, the docs should not stop at:
- one roadmap
- one status doc
- one giant technical summary

The suite needs:
- suite-level docs
- runtime docs
- intended-direction docs
- surface docs
- future-system docs where justified

This prevents:
- patch-lane thinking from dominating product understanding
- mixed truth between current and intended
- under-documenting the parts that already matter

---

## 8. Locked conclusions

- ADG OPS is a suite
- the suite is modular and open to additions
- `licitaciones` is a core technical/conceptual center
- `estadisticas` and `barometro` are not the same thing
- `barometro` deserves its own doc
- surface-first is the right dominant documentation lens
- future additions are real enough to be mapped, but not yet documented as fully current modules

---

## 9. One-line doctrine

**Document ADG OPS as a suite of related surfaces with a real current core and a clearly separated future expansion layer.**
