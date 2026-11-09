# Concordia

**Système multi-agentique d'audit et de conformité dans l'espace OHADA-CEMAC, en commençant par le Cameroun.**

Concordia est un prototype conçu pour le **AI for Good Sandbox Hackathon – United Arab Emirates**, organisé par l'ITU AI for Good Lab. Il explore comment une base de connaissances juridique et réglementaire contextualisée peut alimenter des agents IA spécialisés, coordonnés pour analyser des situations de conformité et rendre leurs conclusions vérifiables.

> **État du projet :** l'ingestion, un index plein texte local interrogeable, une recherche avec citations, une recherche vectorielle locale optionnelle et une première revue de scénarios à événements progressifs sont disponibles. Le modèle vectoriel reste expérimental et doit être évalué sur un jeu plus large relu par des spécialistes. Un modèle génératif, une interface web, la validation juridique des résultats et l'évaluation sur des scénarios experts restent à développer. Ce prototype n'est ni un avis juridique ni une certification de conformité à ITU-T Y.3172.

## Contexte du hackathon

Le hackathon vise la création d'une infrastructure ouverte de connaissances contextualisées par pays et d'agents IA capables d'opérer dans des domaines concrets, en tenant compte des politiques, des lois et des responsabilités institutionnelles. La compétition encourage notamment :

- des bases de connaissances fondées sur des documents publics nationaux et correctement sourcées ;
- des agents spécialisés, par exemple conseiller juridique ou politique, représentant institutionnel ou agent applicatif ;
- des simulations de situations réalistes, avec des informations partielles et distribuées progressivement ;
- la coordination entre agents ayant des rôles et mandats différents ;
- la journalisation et des traces de justification vérifiables : références consultées, étapes, décisions et résultats des agents ;
- l'analyse des lacunes de politiques, de réglementations, de standards et de coordination, éclairée par des exemples internationaux.

Concordia applique cette approche à l'audit et à la conformité juridiques, fiscales et bancaires. Le point de départ est le Cameroun, avec les textes et institutions pertinents pour les espaces OHADA et CEMAC/COBAC. Le périmètre sera étendu au rythme de la constitution et de la validation des sources.

La page officielle décrit les critères d'évaluation et les livrables attendus : [AI for Good Sandbox Hackathon – United Arab Emirates](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/).

## Problème et proposition

Les équipes d'audit et de conformité doivent confronter des documents de nature et de portée différentes : textes juridiques, réglementation sectorielle, règles institutionnelles, politiques et procédures. Une réponse utile doit non seulement repérer une règle pertinente, mais aussi expliquer son application, signaler les incertitudes et permettre à un humain de vérifier les sources.

Concordia vise à transformer ces sources en une base de connaissances exploitable par des agents coordonnés. Dans une démonstration cible, un utilisateur soumet un dossier ou un scénario de conformité ; les agents examinent chacun les éléments correspondant à leur rôle, confrontent leurs conclusions aux sources, puis produisent un rapport d'audit traçable et soumis à validation humaine.

Les résultats sont une aide à l'analyse et ne remplacent ni un avis juridique professionnel ni une décision d'une autorité compétente.

## Critères de réussite visés

La page du hackathon met notamment l'accent sur les aspects suivants. Ils serviront de critères pour les futures validations de Concordia :

- **Qualité de la base** : couverture, exactitude, provenance et structuration des textes ; capacité à retrouver le contexte réglementaire pertinent.
- **Qualité des agents** : pertinence des analyses dans des scénarios réalistes, respect des sources, des mandats et du protocole de coordination.
- **Analyse des lacunes** : identification des ambiguïtés de responsabilités, des écarts de politiques ou de normes et des problèmes de coordination, avec des exemples internationaux pertinents.
- **Auditabilité** : références attribuées aux sources et traces d'exécution suffisamment détaillées pour permettre une revue humaine.
- **Alignement architectural** : prise en compte d'ITU-T Y.3172 et du cadre de préparation à l'IA de l'ITU, sans prétendre à une conformité non démontrée.

## Architecture cible

```text
Textes, règlements, décisions, politiques et documents métier
                            |
                            v
       Collecte, OCR, extraction et normalisation
                            |
                            v
 Base de connaissances versionnée, sourcée et interrogeable
          (index de recherche/RAG et relations juridiques)
                            |
                            v
     Orchestrateur et agents spécialisés par mandat
                            |
             <--- scénarios progressifs --->
                            |
                            v
 Rapport d'audit, références, lacunes et validation humaine
                            |
                            v
         Journal d'audit et traçabilité des échanges
```

Cette architecture reprend le parcours présenté pour le projet : **documents sources → base de connaissances utilisable par les modèles → application de démonstration**. L'objectif est de construire une base réellement interrogeable par les agents, et non de simplement stocker ou citer des documents.

| Étape cible | Rôle dans Concordia | État actuel |
|---|---|---|
| Sources (SRC) | Documents publics et documents métier autorisés, avec juridiction, date, provenance et licence | Des PDF juridiques sont présents localement ; le corpus doit être étendu et sa provenance documentée |
| Collecte et prétraitement (C/PP) | Extraction PDF, OCR si nécessaire, normalisation et segmentation | Pipelines PDF et CCJA disponibles |
| Base de connaissances | Index plein texte, métadonnées, références et relations CCJA | Index SQLite FTS5 local ; les références d'articles, de sections et de pages sont conservées |
| Modèles et agents (M) | Recherche fondée sur les sources, analyse documentaire et rôles spécialisés | Agent juridique extractif et agent d'audit documentaire ; pas de modèle génératif configuré |
| Politique et coordination | Mandats, règles de priorité, protocole d'échange et désaccords entre agents | Orchestration simple des contrôles d'un scénario ; arbitrage multi-institutionnel à construire |
| Scénarios et application | Événements publiés progressivement et restitution | Scénarios JSON traités dans l'ordre par une interface CLI |
| Audit et supervision | Sources citées, résultats observables, limites, validation humaine et journal | Rapport JSON/Markdown et journal JSONL local ; revue humaine requise |

### Alignement avec ITU-T Y.3172

Concordia prend **ITU-T Y.3172** (*Architectural overview of machine learning in future networks including IMT-2020*) comme référence d'architecture pour structurer le cycle allant des sources et du prétraitement aux modèles, à leur utilisation et au suivi. La correspondance détaillée entre les composants de la norme et l'implémentation Concordia reste à préciser et à valider au fur et à mesure du développement. Cet alignement est un objectif de conception, pas une conformité déjà démontrée.

Le projet entend également prendre en compte les perspectives du [ITU AI Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf), notamment l'ouverture et la gouvernance des données, l'adaptation au contexte local, l'inclusion, la supervision humaine et les contraintes d'infrastructure.

## Agents envisagés

Les deux premiers rôles sont disponibles dans une forme initiale ; les rôles institutionnels et une coordination plus avancée restent à construire :

- **Agent d'audit** : analyse les éléments du dossier et relève les points de conformité, les écarts et les informations manquantes.
- **Agent juridique et politique** : recherche les textes applicables, leurs références et leur portée, et signale les incertitudes ou conflits à vérifier.
- **Agent institutionnel** : examine une situation depuis le mandat d'une autorité ou d'un acteur institutionnel défini.
- **Orchestrateur** : distribue les informations et tâches, coordonne les analyses indépendantes, conserve les désaccords et prépare une synthèse.

La page du hackathon demande une journalisation d'audit et des traces de raisonnement. Le prototype journalise les événements, les contrôles et les références récupérées ; il ne prétend pas exposer un raisonnement interne de modèle. La traçabilité repose sur des éléments vérifiables : sources récupérées, citations, entrées et sorties d'agents, étapes du scénario, horodatage et décisions de validation humaine.

## Démonstration envisagée

Une démonstration du projet pourra prendre la forme d'un scénario d'audit de conformité. Les événements et pièces du dossier seront communiqués par étapes, afin que les agents traitent une situation où les informations ne sont pas nécessairement complètes ni distribuées simultanément. Le rapport final devra distinguer :

1. les faits et pièces reçus ;
2. les règles et documents retrouvés, avec leurs références ;
3. les analyses produites par chaque rôle ;
4. les convergences, désaccords, lacunes et points non vérifiés ;
5. les recommandations ou actions proposées, avec les limites et la validation humaine requise.

Les scénarios et résultats devront être évalués sur des cas représentatifs, sans présenter les sorties du prototype comme des décisions juridiques définitives.

## État des lieux du dépôt

### Disponible

- [`src/ingestion/ingest.py`](src/ingestion/ingest.py) : extraction et segmentation de PDF juridiques ; les sorties JSON sont nommées à partir de l'empreinte du fichier. À la relance, un PDF inchangé dont la sortie est valide est ignoré ; un PDF modifié ou une sortie absente ou invalide entraîne un nouveau traitement.
- [`src/ingestion/ingest_ccja.py`](src/ingestion/ingest_ccja.py) : conversion d'un corpus CCJA CSV en documents JSONL et en segments de recherche ; rattachement facultatif de relations déjà présentes dans des fichiers CSV du graphe.
- [`src/knowledge/index.py`](src/knowledge/index.py) : construction d'un index local SQLite FTS5, recherche plein texte en français, citations par article/page et chargement des relations CCJA.
- [`src/agents/legal_policy_agent.py`](src/agents/legal_policy_agent.py) et [`src/agents/auditor_agent.py`](src/agents/auditor_agent.py) : recherche extractive sourcée et identification des pièces manquantes déclarées par un scénario, sans conclusion automatique de conformité.
- [`src/orchestrator/coordinator.py`](src/orchestrator/coordinator.py) : traitement séquentiel des événements et production d'un rapport ainsi que d'un journal d'audit JSONL.
- [`src/app.py`](src/app.py) : commandes CLI pour créer l'index, poser une question, lancer un audit et consulter des relations CCJA.
- [`requirements.txt`](requirements.txt) : dépendances envisagées pour le projet, dont des bibliothèques d'API, de traitement documentaire, de recherche vectorielle et de graphe.

### À construire ou valider

- évaluation et amélioration du rappel/précision de la recherche sur des questions juridiques validées ;
- recherche vectorielle et/ou modèle génératif, si retenus, avec citations vérifiables ;
- ingestion complète et documentée des sources nationales et régionales pertinentes ;
- agents institutionnels, mandats, arbitrage et protocole d'échange multi-acteurs ;
- interface de démonstration et supervision humaine interactive ;
- validation juridique et métier du rapport sur des scénarios réalistes ;
- tests de qualité de recherche, de conformité des réponses, de robustesse et de performance ;
- documentation technique finale et démonstration vidéo, selon les exigences et le calendrier officiels.

Le répertoire `src/policy/` et plusieurs documents de conception restent vides ; ils ne représentent pas encore une couche de politique ou de priorité des normes opérationnelle.

## Données et provenance

Les scripts d'ingestion utilisent les chemins suivants par défaut :

- PDF juridiques : `data/raw_legal_docs/` ;
- corpus CCJA : `data/knowledge_graphs/ccja_jurisprudence/ccja_corpus/full_dataset.csv` ;
- relations CCJA : `data/knowledge_graphs/ccja_jurisprudence/ccja_corpus/ohada_graph/` ;
- documents et segments JSON/JSONL : `02_PROCESSED_JSON/`.

Le corpus CCJA est traité séparément des PDF. L'indexeur inclut les décisions, leurs segments et les relations disponibles dans les JSONL ; la commande de construction crée un index plein texte SQLite local, pas un index vectoriel ou une base distribuée.

Pour chaque jeu de données publié ou partagé, documenter au minimum l'organisation source, l'URL ou la référence, la juridiction, la date/version, la licence et les transformations appliquées. Vérifier les droits de réutilisation et de redistribution avant de publier des documents ou des résultats dérivés. Les sorties produites localement ne sont pas nécessairement incluses dans le dépôt Git.

## Installation

Prérequis : Python 3.10 ou plus récent. Pour l'OCR des PDF numérisés, installer également Tesseract et les données de langue française sur Ubuntu :

```bash
sudo apt install tesseract-ocr tesseract-ocr-fra
```

Créer un environnement virtuel et installer les dépendances :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Utilisation

Lancer le pipeline PDF depuis la racine du dépôt :

```bash
python -m src.ingestion.ingest
```

Le pipeline parcourt `data/raw_legal_docs/` et écrit un fichier JSON par PDF traité dans `02_PROCESSED_JSON/`. Les documents déjà traités et inchangés sont sautés à la relance.

Importer le corpus CCJA avec les chemins par défaut :

```bash
python -m src.ingestion.ingest_ccja
```

Les fichiers produits par défaut sont :

- `02_PROCESSED_JSON/ccja-decisions.jsonl` : une décision normalisée par ligne ;
- `02_PROCESSED_JSON/ccja-search-chunks.jsonl` : segments de texte associés à leur décision et à leur champ source.

Les paramètres `--csv`, `--graph-dir`, `--output`, `--chunks-output`, `--chunk-size` et `--chunk-overlap` permettent d'adapter les chemins et le découpage. Voir l'aide de la commande :

```bash
python -m src.ingestion.ingest_ccja --help
```

### Construire ou actualiser la base de connaissances

Depuis la racine du dépôt, après avoir produit les documents JSON et JSONL :

```bash
python -m src.app build-index
```

Cette commande indexe les JSON dans `02_PROCESSED_JSON/`, ainsi que les décisions et segments CCJA s'ils sont présents. L'index SQLite est créé localement dans `data/knowledge_base/concordia.sqlite3` et n'est pas ajouté à Git. Chaque reconstruction remplace son contenu avec les fichiers présents à cet instant.

### Poser une question documentaire

```bash
python -m src.app ask "Quelles dispositions concernent l'immatriculation au RCCM ?"
```

La réponse restitue des extraits de l'index avec le titre, l'article ou la section, la page et le fichier source. Cette première version utilise SQLite FTS5 ; elle ne génère pas de synthèse par modèle et ne constitue pas un avis juridique.

### Router une demande

La commande `route` reconnaît de façon déterministe les deux parcours disponibles : recherche juridique et audit documentaire. Elle n'utilise pas de modèle d'intention ; une demande ambiguë ou non reconnue est refusée plutôt que routée par défaut. Pour lever l'ambiguïté, préciser `--intent`. Un audit nécessite toujours un scénario JSON :

```bash
python -m src.app route "Quels articles parlent de l'immatriculation ?"
python -m src.app route "Lancer un audit de conformité" --scenario data/scenarios/cameroon_company_document_review.json
python -m src.app route "Auditer ce dossier et rechercher les articles applicables" --intent document_audit --scenario data/scenarios/cameroon_company_document_review.json
```

Le routeur couvre uniquement ces deux parcours ; les analyses institutionnelles, les modèles génératifs et les décisions automatiques ne sont pas pris en charge.

### Mesurer la recherche documentaire

Un premier benchmark de deux questions et de leurs articles sources attendus est fourni dans `data/evaluation/legal_retrieval.json`. Les références ont été contrôlées dans les fichiers du corpus ; ce jeu n'a pas encore été validé par un expert juridique. Il mesure le rappel, le rang réciproque, la présence de citations et la latence, sans noter la justesse d'une interprétation juridique :

```bash
python -m src.app evaluate-search data/evaluation/legal_retrieval.json --top-k 5
```

Cette mesure constitue une base FTS de départ. Les modes vectoriel et hybride sont disponibles, mais leurs scores sur ce petit jeu ne seront interprétés qu'après revue des questions et références par une personne qualifiée ; ils ne sont pas généralisables à l'ensemble des recherches.

### Activer la recherche vectorielle locale

Le parcours FTS reste le défaut. Pour calculer localement les vecteurs des passages, installer les dépendances, puis reconstruire l'index avec le modèle multilingue Sentence Transformers (384 dimensions) :

```bash
pip install -r requirements.txt
python -m src.app build-index --vector-model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Le premier lancement télécharge les poids du modèle depuis Hugging Face ; l'encodage des documents et des requêtes s'exécute ensuite sur CPU. Les vecteurs sont conservés dans la base SQLite locale. Le choix du mode reste explicite :

```bash
python -m src.app ask "Quel texte porte le Code électoral camerounais ?" --retrieval-mode fts
python -m src.app ask "Quel identifiant commercial doit apparaître dans un avis publié par une société ?" --retrieval-mode vector
python -m src.app ask "Quel identifiant commercial doit apparaître dans un avis publié par une société ?" --retrieval-mode hybrid
python -m src.app evaluate-search data/evaluation/legal_retrieval.json --retrieval-mode hybrid
```

Le mode hybride fusionne les classements lexical et vectoriel par Reciprocal Rank Fusion ; les scores bruts des deux moteurs ne sont pas comparables. La recherche vectorielle ne génère pas de réponse : les résultats restent des extraits de documents avec leurs citations. Le modèle local n'est pas encore évalué sur un benchmark validé par un juriste.

### Lancer un scénario de revue progressive

```bash
python -m src.app audit data/scenarios/cameroon_company_document_review.json
```

Le scénario d'exemple transmet un dossier initial, puis une pièce complémentaire. Les événements sont évalués dans l'ordre ; les pièces manquantes sont celles déclarées par le scénario, et non une conclusion de non-conformité légale. Le rapport JSON et son journal JSONL sont écrits localement dans `data/audits/`.

### Consulter les relations CCJA indexées

```bash
python -m src.app graph OHADA-CCJA-00000
```

Ces relations sont celles présentes dans le corpus importé ; elles ne sont pas une interprétation juridique autonome.

### Tests

```bash
python -m unittest discover -s tests
```

## Livrables de la compétition

Selon la [page officielle du hackathon](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/), les éléments de soumission comprennent :

1. un rapport technique de cinq pages maximum ;
2. le dépôt GitHub du projet ;
3. une base de connaissances contenant politiques, réglementations et stratégies ;
4. facultativement, une vidéo de démonstration de sept minutes maximum (requise pour les équipes présélectionnées selon la page).

Le code de création de la base, la base elle-même, les rapports et la démonstration devront être préparés et vérifiés avant soumission. Consulter la page officielle pour les dates, modalités, règles d'équipe et éventuelles mises à jour.

## Références

- [AI for Good Sandbox Hackathon – United Arab Emirates](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/)
- [Recommandation ITU-T Y.3172](https://www.itu.int/rec/T-REC-Y.3172/en)
- [ITU AI Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf)
- [ITU AI for Good Lab](https://aiforgood.itu.int/)

## Équipe

Projet développé par l'équipe de l'Université de Yaoundé I pour l'ITU AI for Good.
