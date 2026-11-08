# Concordia ⚖️🤖

**Système Multi-Agents d'Audit et de Conformité Juridique, Fiscal et Bancaire (Zone OHADA / CEMAC)**

Projet développé dans le cadre du **Hackathon ITU AI for Good Lab**.

---

## 📌 Présentation du Projet

**Concordia** est un système multi-agents intelligent et souverain conçu pour automatiser l'audit de conformité des contrats, des statuts d'entreprises et des flux financiers au sein de l'espace **OHADA** et de la zone **CEMAC / COBAC**. 

---

## 🏛️ Alignement avec l'Architecture ITU-T Y.3172

| Composant ITU-T Y.3172 | Module Concordia | Rôle dans le Système |
| :--- | :--- | :--- |
| **SRC** (Source) | `01_RAW_STORAGE/` | Collecte des documents bruts |
| **C & PP** (Collector / Preprocessing) | `src/ingestion/` | Pipelines d'OCR et normalisation JSON |
| **M** (Model) | `src/rag/` | Moteur RAG hybride |
| **P** (Policy) | `src/graph/` & `src/agents/` | Poset de Primauté (Hiérarchie des normes) |
| **D** (Distributor) | `src/audit/` | Traçabilité des décisions |
| **SINK** (Inference Target) | `src/agents/` & UI | Restitution des rapports |

---

## 👥 Équipe et Contribution
Projet développé par l'équipe de l'Université de Yaoundé I pour l'ITU AI for Good.
