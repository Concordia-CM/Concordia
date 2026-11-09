# Concordia

**Système multi-agentique d'audit et de conformité dans l'espace OHADA-CEMAC, en commençant par le Cameroun.**

Concordia est un prototype conçu pour le **AI for Good Sandbox Hackathon – United Arab Emirates**, organisé par l'ITU AI for Good Lab. Il explore comment une base de connaissances juridique et réglementaire contextualisée peut alimenter des agents IA spécialisés, coordonnés pour analyser des situations de conformité et rendre leurs conclusions vérifiables.

> **État du projet :** l'ingestion, un index plein texte local interrogeable, une recherche avec citations, une recherche vectorielle locale optionnelle, une génération Ollama optionnelle, une revue de scénarios et une première interface web locale pour le dépôt de documents sont disponibles. Les modèles et résultats restent expérimentaux et doivent être évalués par des spécialistes. L'orchestration complète multi-agent et la validation juridique restent à développer. Ce prototype n'est ni un avis juridique ni une certification de conformité à ITU-T Y.3172.

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

### Déposer un dossier confidentiel

L'interface web de démonstration accepte des PDF (y compris les scans si Tesseract est disponible) et des fichiers DOCX. Elle est configurée pour écouter uniquement sur `127.0.0.1`, avec la télémétrie Streamlit désactivée. Les fichiers sont traités localement en mémoire, dans les limites documentées par l'interface ; leur texte n'est pas ajouté à l'index des sources juridiques. Le traitement cloud n'est pas configuré dans cette version.

```bash
streamlit run src/web_app.py
```

Le réviseur saisit les questions de contrôle et les éléments attendus ; Concordia vérifie leur présence par correspondance lexicale et retrouve les sources juridiques dans l'index existant. Cette première tranche ne détermine pas les obligations applicables, l'authenticité ou la validité des pièces ; aucun référentiel d'audit RCCM juridiquement validé n'est encore fourni. Les résultats restent en mémoire, ne sont pas enregistrés automatiquement et leur téléchargement exige une confirmation à chaque audit. L'interface demande à chaque audit si les originaux doivent rester en mémoire durant la session ou être supprimés ; un bouton permet aussi d'effacer le rapport et l'état de session. N'exposer cette interface sur un réseau ou un serveur distant qu'après avoir défini une politique de sécurité et de conservation adaptée : les fichiers envoyés à une instance distante transiteraient vers cette instance.

Cette architecture reprend le parcours présenté pour le projet : **documents sources → base de connaissances utilisable par les modèles → application de démonstration**. L'objectif est de construire une base réellement interrogeable par les agents, et non de simplement stocker ou citer des documents.

| Étape cible | Rôle dans Concordia | État actuel |
|---|---|---|
| Sources (SRC) | Documents publics et documents métier autorisés, avec juridiction, date, provenance et licence | Des PDF juridiques sont présents localement ; le corpus doit être étendu et sa provenance documentée |
| Collecte et prétraitement (C/PP) | Extraction PDF, OCR si nécessaire, normalisation et segmentation | Pipelines PDF et CCJA disponibles |
| Base de connaissances | Index plein texte et vectoriel, métadonnées, références et relations CCJA | Index SQLite FTS5 ; la recherche juridique privilégie par défaut les textes et exclut la doctrine/manuels et les arrêts CCJA ; embeddings multilingues optionnels |
| Modèles et agents (M) | Recherche fondée sur les sources, analyse documentaire et rôles spécialisés | Agent juridique, agent d'audit documentaire et agent institutionnel ; synthèse Ollama explicitement activée |
| Politique et coordination | Contrôles de provenance, mandats, protocole d'échange et désaccords entre agents | Première Policy déterministe : vérification exacte des passages/citations indexés et revue humaine obligatoire ; orchestration multi-agent et arbitrage à construire |
| Scénarios et application | Événements publiés progressivement et restitution | Scénarios JSON via CLI et première interface web locale avec dépôt confidentiel de PDF/DOCX |
| Audit et supervision | Sources citées, résultats observables, limites, validation humaine et journal | Rapport JSON/Markdown et journal JSONL local ; revue humaine requise |

### Alignement avec ITU-T Y.3172

Concordia prend **ITU-T Y.3172** (*Architectural overview of machine learning in future networks including IMT-2020*) comme référence d'architecture pour structurer le cycle allant des sources et du prétraitement aux modèles, à leur utilisation et au suivi. La correspondance détaillée entre les composants de la norme et l'implémentation Concordia reste à préciser et à valider au fur et à mesure du développement. Cet alignement est un objectif de conception, pas une conformité déjà démontrée.

Le projet entend également prendre en compte les perspectives du [ITU AI Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf), notamment l'ouverture et la gouvernance des données, l'adaptation au contexte local, l'inclusion, la supervision humaine et les contraintes d'infrastructure.

## Agents envisagés

Les rôles disponibles sont des premières versions documentaires :

- **Agent d'audit** : analyse les éléments du dossier et relève les points de conformité, les écarts et les informations manquantes.
- **Agent juridique et politique** : recherche les textes applicables, leurs références et leur portée, et signale les incertitudes ou conflits à vérifier.
- **Agent institutionnel** : examine une situation à partir d'une institution, d'un mandat et d'une juridiction fournis explicitement via `route --intent institutional_analysis`. Il ne représente pas une position officielle et ses résultats restent soumis à une revue humaine.
- **Orchestrateur** : distribue les informations et tâches, coordonne les analyses indépendantes, conserve les désaccords et prépare une synthèse.

L'analyse institutionnelle peut être lancée directement :

```bash
python -m src.app route "Examiner les obligations de déclaration" \
  --intent institutional_analysis \
  --institution "Autorité de supervision" \
  --mandate "Examiner les obligations de déclaration" \
  --jurisdiction "Cameroun"
```

Elle peut aussi être activée dans un scénario d'audit en ajoutant une configuration facultative au niveau racine :

```json
{
  "institutional_review": {
    "institution": "Autorité de supervision",
    "mandate": "Examiner les obligations de déclaration",
    "jurisdiction": "Cameroun",
    "generate": false
  }
}
```

L'orchestrateur applique cette perspective à chaque contrôle, puis ajoute le résultat, les références et la décision Policy au rapport et au journal d'audit. `generate` reste désactivé par défaut ; l'activer nécessite un serveur Ollama configuré. L'analyse interroge actuellement le même index documentaire général que l'agent juridique : aucun corpus institutionnel dédié n'est encore fourni.

La page du hackathon demande une journalisation d'audit et des traces de raisonnement. Le prototype journalise les événements, les contrôles et les références récupérées ; il ne prétend pas exposer un raisonnement interne de modèle. La traçabilité repose sur des éléments vérifiables : sources récupérées, citations, entrées et sorties d'agents, étapes du scénario, horodatage et décisions de validation humaine.

## Démonstration envisagée

Une démonstration du projet pourra prendre la forme d'un scénario d'audit de conformité. Les événements et pièces du dossier seront communiqués par étapes, afin que les agents traitent une situation où les informations ne sont pas nécessairement complètes ni distribuées simultanément. Le rapport final devra distinguer :

1. les faits et pièces reçus ;
2. les règles et documents retrouvés, avec leurs références ;
3. les analyses produites par chaque rôle ;
4. les convergences, désaccords, lacunes et points non vérifiés ;
5. les recommandations ou actions proposées, avec les limites et la validation humaine requise.

Les scénarios et résultats devront être évalués sur des cas représentatifs, sans présenter les sorties du prototype comme des décisions juridiques définitives.

### Brouillon de préparation comptable

L'interface web propose une checklist indicative de préparation pour une revue comptable, organisée par rubriques de pièces et contrôles documentaires. Le modèle est enregistré dans [`data/checklists/accounting_readiness_draft.json`](data/checklists/accounting_readiness_draft.json), reste explicitement au statut `draft_unvalidated` et les identifiants sélectionnés sont consignés dans le rapport. Il s'inspire des catégories du texte commercial partagé, mais n'en reprend ni les seuils ni les affirmations juridiques. Il n'est ni exhaustif ni validé juridiquement : les rubriques sélectionnées doivent être adaptées au mandat et vérifiées par un professionnel. Les recherches lexicales de pièces ne déterminent pas leur authenticité, suffisance ou conformité.

## État des lieux du dépôt

### Disponible

- [`src/ingestion/ingest.py`](src/ingestion/ingest.py) : extraction et segmentation de PDF juridiques ; les sorties JSON sont nommées à partir de l'empreinte du fichier. À la relance, un PDF inchangé dont la sortie est valide est ignoré ; un PDF modifié ou une sortie absente ou invalide entraîne un nouveau traitement.
- [`src/ingestion/ingest_ccja.py`](src/ingestion/ingest_ccja.py) : conversion d'un corpus CCJA CSV en documents JSONL et en segments de recherche ; rattachement facultatif de relations déjà présentes dans des fichiers CSV du graphe.
- [`src/knowledge/index.py`](src/knowledge/index.py) : construction d'un index local SQLite FTS5, recherche plein texte en français, citations par article/page et chargement des relations CCJA.
- [`src/agents/legal_policy_agent.py`](src/agents/legal_policy_agent.py), [`src/agents/auditor_agent.py`](src/agents/auditor_agent.py) et [`src/agents/institutional_agent.py`](src/agents/institutional_agent.py) : recherche sourcée, identification des pièces manquantes et perspective institutionnelle configurée, sans conclusion automatique de conformité.
- [`src/orchestrator/coordinator.py`](src/orchestrator/coordinator.py) : traitement séquentiel des événements et production d'un rapport ainsi que d'un journal d'audit JSONL.
- [`src/app.py`](src/app.py) : commandes CLI pour créer l'index, poser une question, lancer un audit et consulter des relations CCJA.
- [`src/web_app.py`](src/web_app.py) : première interface locale de revue documentaire ; les contrôles sont définis par le réviseur, les pièces sont extraites en mémoire et ne sont ni indexées dans le corpus juridique ni envoyées à un service externe.
- [`requirements.txt`](requirements.txt) : dépendances envisagées pour le projet, dont des bibliothèques d'API, de traitement documentaire, de recherche vectorielle et de graphe.

### À construire ou valider

- évaluation comparative FTS/vectoriel/hybride sur un benchmark plus large relu par des spécialistes ;
- évaluation experte des synthèses Ollama/RAG et qualité juridique des citations ;
- ingestion complète et documentée des sources nationales et régionales pertinentes ;
- corpus réglementaire institutionnel dédié, mandats documentés, arbitrage et protocole d'échange multi-acteurs ;
- interface de démonstration et supervision humaine interactive ;
- validation juridique et métier du rapport sur des scénarios réalistes ;
- tests de qualité de recherche, de conformité des réponses, de robustesse et de performance ;
- documentation technique finale et démonstration vidéo, selon les exigences et le calendrier officiels.

Le répertoire `src/policy/` contient maintenant une première Policy de provenance dans `src/policy/legal_policy.py`. Elle bloque une référence absente ou falsifiée et requiert une revue humaine pour les autres sorties ; elle ne vérifie ni la portée juridique ni la priorité des normes. Les contrats partagés et un client Ollama optionnel sont disponibles ; l'agent institutionnel est routable et peut être inclus dans un scénario d'audit, mais interroge le même index général faute de corpus dédié. La coordination multi-agent avec arbitrage reste à construire.

### Configuration et Ollama

La configuration se lit depuis les variables d'environnement :

| Variable | Défaut | Usage |
|---|---|---|
| `CONCORDIA_DATABASE_PATH` | `data/knowledge_base/concordia.sqlite3` | Chemin de la base locale |
| `CONCORDIA_EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Modèle d'embeddings |
| `CONCORDIA_OLLAMA_BASE_URL` | `http://localhost:11434` | Adresse du serveur Ollama local |
| `CONCORDIA_OLLAMA_MODEL` | `qwen2.5:3b` | Modèle génératif Ollama local ; définir la variable vide pour le désactiver |
| `CONCORDIA_LLM_TIMEOUT_SECONDS` | `120` | Timeout prévu pour les appels génératifs |

Le modèle par défaut est un choix de démarrage léger, pas une recommandation pour prendre des décisions juridiques. L'option `--generate` déclenche explicitement un appel Ollama ; les sorties sont limitées aux passages récupérés, leurs références sont vérifiées par Policy et une revue humaine reste obligatoire.

Installer et lancer Ollama, puis télécharger le modèle :

```bash
ollama pull qwen2.5:3b
```

Sans `--generate`, les commandes gardent le comportement extractif et ne contactent pas Ollama. Pour activer la synthèse :

```bash
python -m src.app ask "Quel texte porte le Code électoral camerounais ?" --generate
python -m src.app route "Quels articles parlent de l'immatriculation ?" --generate
```

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

La commande `ask` limite par défaut les résultats aux textes juridiques : les décisions CCJA et les documents classés comme doctrine/manuels ne sont pas mélangés à ces résultats. Une requête contenant `RCCM` privilégie les articles de loi qui mentionnent le registre, y compris lorsque le texte développe l'acronyme en « Registre du Commerce et du Crédit Mobilier ». Pour une recherche de jurisprudence ou une recherche tous corpus confondus, utiliser `--source-scope case_law` ou `--source-scope all`. Ce filtre s'applique aussi aux modes vectoriel et hybride et ne nécessite pas de reconstruire l'index existant.

```bash
python -m src.app ask "Immatriculation au RCCM" --source-scope case_law
python -m src.app ask "Immatriculation au RCCM" --source-scope all
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

Le benchmark `data/evaluation/legal_retrieval.json` contient douze questions à visée de revue documentaire couvrant notamment le RCCM, le droit du travail, la protection du consommateur, le crédit, la concurrence et le référentiel comptable SYCEBNL. Chaque cas indique un domaine, un point de contrôle, une ou plusieurs références attendues, et parfois un passage distracteur. Les références ont été contrôlées dans les fichiers locaux du corpus ; ce jeu n'a pas encore été validé par un expert juridique et ne certifie ni l'autorité ni la version en vigueur des textes. Il mesure le rappel, la précision@5, le rang réciproque, la présence de citations et la latence, sans noter la justesse d'une interprétation juridique ni la qualité d'une checklist. La recherche d'une question RCCM utilise aussi la hiérarchie des titres et sections pour prioriser les dispositions classées sous l'immatriculation ; ce signal améliore le classement, mais ne valide pas leur applicabilité :

```bash
python -m src.app evaluate-search data/evaluation/legal_retrieval.json --top-k 5
```

L'évaluation utilise par défaut le périmètre des textes juridiques, hors doctrine et jurisprudence CCJA ; `--source-scope all` permet de changer ce périmètre. Cette mesure est un point de départ FTS, pas une preuve de qualité générale. Les questions, références attendues et distracteurs doivent encore être revus par un professionnel du droit avant de servir de référence. Les points de contrôle sont des axes de recherche, pas une checklist réglementaire exhaustive ou validée.

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
