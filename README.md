# Concordia ⚖️🤖 (ITU AI for Good Lab)

**Système Multi-Agents Autonome d'Audit et de Conformité Juridique, Fiscale et Bancaire (Zone OHADA / CEMAC)**

[![ITU-T Y.3172](https://img.shields.io/badge/ITU--T-Y.3172%20Aligned-blue.svg)](https://www.itu.int)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%252B-blue.svg)](https://www.python.org/)

---

## 📌 1. Vue d'ensemble du Projet

**Concordia** est un système multi-agents intelligent, souverain et auditable conçu pour automatiser l'analyse, l'évaluation et l'audit de conformité réglementaire au sein de l'espace **OHADA** (Organisation pour l'Harmonisation en Afrique du Droit des Affaires) et de la zone **CEMAC / COBAC** (Commission Bancaire de l'Afrique Centrale).

Dans un contexte économique marqué par la complexité et l'enchevêtrement des normes (Actes Uniformes, instructions BEAC, circulaires COBAC, législations nationales et fiscalité locale), Concordia remédie aux asymétries d'information et aux risques juridiques en orchestrant des agents spécialisés dotés d'une base de connaissances vectorisée et structurée.

---

## 🏛️ 2. Alignement avec l'Architecture ITU-T Y.3172

L'architecture technique de Concordia est strictement alignée sur le cadre standardisé de déploiement de l'apprentissage automatique et de l'IA de l'UIT (**ITU-T Y.3172**), garantissant interopérabilité, gouvernance et traçabilité de bout en bout :

| Composant ITU-T Y.3172 | Module Concordia | Implémentation Technique & Rôle |
| :--- | :--- | :--- |
| **SRC** (Source) | `01_RAW_STORAGE/` | Collecte sécurisée des corpus documentaires bruts (PDF juridiques, codes généraux, traités). |
| **C & PP** (Collector / Preprocessing) | `src/ingestion/` | Pipelines d'extraction (`PyMuPDF`), OCR de secours (`PyTesseract`) et chunking sémantique en JSON. |
| **M** (Model) | `src/rag/` | Moteur de recherche hybride (BM25 + embeddings vectoriels) hébergeant la base de connaissances. |
| **P** (Policy / Poset de Primauté) | `src/graph/` & `src/agents/` | Graphe de connaissances (`Neo4j`) modélisant la hiérarchie des normes (OHADA > COBAC > Lois nationales). |
| **D** (Distributor) | `src/audit/` | Mécanismes de traçabilité, journaux d'audit et consignation de la chaîne de pensée (*Chain-of-Thought*). |
| **SINK** (Inference Target) | `src/agents/` & Interface | Restitution des rapports de non-conformité, alertes de risques et recommandations correctives. |

---

## 👥 3. Rôles et Orchestration Multi-Agents

Concordia simule un écosystème institutionnel et décisionnel à travers plusieurs agents interconnectés :
* **Le Conseiller Juridique et Politique** : Analyse la conformité des statuts, contrats et clauses au regard du droit des affaires OHADA.
* **L'Auditeur Bancaire et Prudentiel (COBAC)** : Évalue l'exposition aux risques réglementaires, le respect des ratios prudentiels et la conformité des flux de change CEMAC.
* **L'Acteur Institutionnel / Régulateur** : Joue le rôle d'arbitre inter-domaines en cas de scénarios d'erreurs ou de conflits normatifs.

---

## 📂 4. Structure Détaillée du Dépôt

```text
concordia/
│
├── .github/workflows/          # Pipelines CI/CD et tests automatisés
├── 01_RAW_STORAGE/             # [SRC] Corpus documentaire brut (exclu de Git via .gitignore)
├── 02_PROCESSED_JSON/          # [PP] Données nettoyées, chunkées et prêtes pour la KB
├── docs/                       # 📄 Documentation officielle & Rapport technique (max 5 pages)
│   ├── technical_report.md     # Rapport complet soumis pour l'ITU
│   └── ITU_Y3172_mapping.md    # Documentation détaillée de l'alignement normatif
├── src/                        # Code source du système
│   ├── pipeline/               # Orchestration du pipeline ITU-T Y.3172
│   ├── agents/                 # Logique des agents (Juridique, Bancaire, Régulateur)
│   ├── rag/                    # Pipeline RAG et moteurs de recherche
│   ├── graph/                  # Nœud P : Graphe Neo4j pour la hiérarchie des normes
│   └── audit/                  # Traçabilité, logging et chaînes de pensée
├── tests/                      # Tests unitaires et d'intégration
├── requirements.txt            # Dépendances Python du projet
└── README.md                   # Documentation principale

🚀 5. Guide d'Installation et de Démarrage Rapide
Étape 1 : Cloner le dépôt et configurer l'environnement
Bash

git clone [https://github.com/NOM_DE_TON_ORGANISATION/concordia.git](https://github.com/NOM_DE_TON_ORGANISATION/concordia.git)
cd concordia

# Création et activation de l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

Étape 2 : Installer les dépendances
Bash

pip install --upgrade pip
pip install -r requirements.txt

Étape 3 : Configurer les variables d'environnement
Bash

cp .env.example .env
# Éditer le fichier .env pour y renseigner vos clés API et identifiants Neo4j

🛠️ 6. Contribution et Équipe

Projet développé par l'équipe de recherche de l'Université de Yaoundé I dans le cadre du hackathon ITU AI for Good Lab.

Pour contribuer, veuillez suivre le workflow par branches :

    Créez une branche thématique : git checkout -b feature/nom-de-la-fonctionnalite

    Validez vos modifications : git commit -m "feat: description claire de l'apport"

    Poussez sur le dépôt distant : git push origin feature/nom-de-la-fonctionnalite

    Ouvrez une Pull Request vers la branche main pour revue par les pairs.

📜 7. Licence

Distribué sous licence MIT. Voir le fichier LICENSE pour plus d'informations.
