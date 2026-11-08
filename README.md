# Concordia

**Système multi-agentique d'audit et de conformité dans l'espace OHADA-CEMAC, en commençant par le Cameroun.**

Concordia est un prototype conçu pour le **AI for Good Sandbox Hackathon – United Arab Emirates**, organisé par l'ITU AI for Good Lab. Il explore comment une base de connaissances juridique et réglementaire contextualisée peut alimenter des agents IA spécialisés, coordonnés pour analyser des situations de conformité et rendre leurs conclusions vérifiables.

> **État du projet :** le dépôt contient actuellement des pipelines d'ingestion et de préparation de données juridiques. La base vectorielle ou graphe interrogeable, les agents, leur orchestration, les scénarios interactifs et l'interface d'audit restent à implémenter. Concordia est donc un prototype en construction, et non une solution complète ou une certification de conformité à ITU-T Y.3172.

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
| Base de connaissances | Indexation vectorielle et/ou plein texte, métadonnées et relations juridiques | L'importeur CCJA prépare des JSONL et des segments ; aucun index interrogeable n'est créé par ces scripts |
| Modèles et agents (M) | Recherche augmentée par les sources, analyse de conformité et rôles institutionnels spécialisés | À implémenter |
| Politique et coordination | Mandats, règles de priorité, protocole d'échange et désaccords entre agents | À implémenter |
| Scénarios et application | Événements publiés progressivement, interaction utilisateur et restitution | À implémenter |
| Audit et supervision | Sources citées, décisions observables, limites, validation et journal d'audit | À implémenter |

### Alignement avec ITU-T Y.3172

Concordia prend **ITU-T Y.3172** (*Architectural overview of machine learning in future networks including IMT-2020*) comme référence d'architecture pour structurer le cycle allant des sources et du prétraitement aux modèles, à leur utilisation et au suivi. La correspondance détaillée entre les composants de la norme et l'implémentation Concordia reste à préciser et à valider au fur et à mesure du développement. Cet alignement est un objectif de conception, pas une conformité déjà démontrée.

Le projet entend également prendre en compte les perspectives du [ITU AI Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf), notamment l'ouverture et la gouvernance des données, l'adaptation au contexte local, l'inclusion, la supervision humaine et les contraintes d'infrastructure.

## Agents envisagés

Les rôles suivants décrivent la cible fonctionnelle ; ils ne sont pas encore implémentés :

- **Agent d'audit** : analyse les éléments du dossier et relève les points de conformité, les écarts et les informations manquantes.
- **Agent juridique et politique** : recherche les textes applicables, leurs références et leur portée, et signale les incertitudes ou conflits à vérifier.
- **Agent institutionnel** : examine une situation depuis le mandat d'une autorité ou d'un acteur institutionnel défini.
- **Orchestrateur** : distribue les informations et tâches, coordonne les analyses indépendantes, conserve les désaccords et prépare une synthèse.

La page du hackathon demande une journalisation d'audit et des traces de raisonnement. La conception devra éviter de confondre une génération de texte explicative avec une preuve du raisonnement interne d'un modèle. La traçabilité visée repose sur des éléments vérifiables : sources récupérées, citations, entrées et sorties d'agents, résumés de justification, étapes du scénario, horodatage et décisions de validation humaine.

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
- [`requirements.txt`](requirements.txt) : dépendances envisagées pour le projet, dont des bibliothèques d'API, de traitement documentaire, de recherche vectorielle et de graphe.

### À construire ou valider

- index vectoriel/plein texte ou graphe réellement consultable par les agents ;
- ingestion complète et documentée des sources nationales et régionales pertinentes ;
- orchestrateur, agents, mandats et protocole de coordination ;
- scénarios interactifs à événements progressifs ;
- application de démonstration et génération du rapport d'audit ;
- journalisation structurée, citations de sources, supervision et évaluation ;
- tests de qualité de recherche, de conformité des réponses, de robustesse et de performance ;
- documentation technique finale et démonstration vidéo, selon les exigences et le calendrier officiels.

Les répertoires `src/agents/`, `src/orchestrator/`, `src/policy/` et `src/sink/` ainsi que plusieurs documents de conception sont actuellement des emplacements de projet vides ; leur présence ne signifie pas que les composants associés sont déjà fonctionnels.

## Données et provenance

Les scripts d'ingestion utilisent les chemins suivants par défaut :

- PDF juridiques : `data/raw_legal_docs/` ;
- corpus CCJA : `data/knowledge_graphs/ccja_jurisprudence/ccja_corpus/full_dataset.csv` ;
- relations CCJA : `data/knowledge_graphs/ccja_jurisprudence/ccja_corpus/ohada_graph/` ;
- documents et segments JSON/JSONL : `02_PROCESSED_JSON/`.

Le corpus CCJA est traité séparément des PDF. Les segments produits par l'importeur peuvent servir de base à une étape ultérieure d'indexation, mais leur création ne construit pas à elle seule une base vectorielle.

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

## Utilisation des pipelines disponibles

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
