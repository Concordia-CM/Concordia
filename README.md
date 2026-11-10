# Concordia

**Prototype d'aide à la recherche juridique et à la revue de conformité dans l'espace OHADA-CEMAC, en commençant par le Cameroun.**

Concordia est un prototype conçu pour le **AI for Good Sandbox Hackathon – United Arab Emirates**, organisé par l'ITU AI for Good Lab. Il explore comment une base de connaissances juridique et réglementaire contextualisée peut alimenter des agents IA spécialisés, coordonnés pour analyser des situations de conformité et rendre leurs conclusions vérifiables.

> **Prototype de démonstration — pas un avis juridique.** La recherche documentaire, la réponse Ollama fondée sur les passages retrouvés, les scénarios d'audit CLI et une interface locale de revue PDF/DOCX sont disponibles. La coordination multi-agent complète, les référentiels juridiquement validés et l'évaluation experte restent à construire. Le prototype ne certifie pas la conformité et ne démontre pas une conformité à ITU-T Y.3172.

## En bref pour le jury

**Le problème.** Pour examiner une situation de conformité, il faut rapprocher les faits et pièces d'un dossier de textes provenant de juridictions et de domaines différents, sans perdre la provenance des règles ni masquer les incertitudes.

**La proposition.** Concordia indexe des documents juridiques, retrouve des passages citables et peut demander au modèle Ollama configuré de rédiger une réponse limitée à ces passages. Dans un scénario d'audit, le système distingue les faits déclarés, les pièces attendues et les références juridiques ; la décision finale reste humaine.

**Ce qui est démontrable aujourd'hui.**

- Recherche avec citations dans un index local, avec filtres séparant textes juridiques, jurisprudence CCJA et doctrine.
- Réponses narratives Ollama à partir des sources retenues, ou mode extractif sans génération.
- Scénario d'audit séquentiel en CLI et revue locale de documents PDF/DOCX.
- Contrôle de provenance des citations et résultats marqués comme nécessitant une revue humaine.

**Ce qui n'est pas encore démontré.** La coordination complète de plusieurs agents avec arbitrage, la pertinence juridique des réponses, la validité des pièces et la conformité à un référentiel d'audit doivent être évaluées par des spécialistes. Le benchmark de recherche est un jeu de départ, pas une validation juridique.

**Essai rapide** (après installation et préparation de l'index, décrites plus bas) :

```bash
# Poser une question sans génération
python -m src.app ask "Quelles dispositions concernent l'immatriculation au RCCM ?" --extractive

# Ouvrir la revue documentaire locale
streamlit run src/web_app.py

# Mesurer la recherche sur le jeu de référence
python -m src.app evaluate-search data/evaluation/legal_retrieval.json --top-k 5
```

Le parcours Web n'envoie pas le texte intégral des fichiers à Ollama. Si une génération est activée et qu'une source est retrouvée, l'URL Ollama configurée peut recevoir la question, les noms de fichiers, les faits et éléments attendus ainsi que les extraits juridiques ; vérifier `CONCORDIA_OLLAMA_BASE_URL` avant l'essai.

**Pour approfondir :** [architecture et état d'avancement](#architecture-et-parcours-actuel) · [agents et limites](#agents-disponibles-et-orchestration-cible) · [installation et commandes](#installation) · [évaluation de la recherche](#mesurer-la-recherche-documentaire) · [données et provenance](#données-et-provenance).

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

Concordia vise à transformer ces sources en une base de connaissances exploitable par des agents spécialisés. Aujourd'hui, un utilisateur peut soumettre une question ou lancer un scénario séquentiel ; l'objectif à terme est que des agents coordonnés confrontent leurs analyses aux sources et produisent un rapport traçable soumis à validation humaine.

Les résultats sont une aide à l'analyse et ne remplacent ni un avis juridique professionnel ni une décision d'une autorité compétente.

## Critères de réussite visés

La page du hackathon met notamment l'accent sur les aspects suivants. Le tableau distingue les éléments déjà observables des validations qui restent à faire :

| Critère | État dans Concordia |
|---|---|
| Qualité et provenance du corpus | Index local avec références et filtres de sources ; benchmark de 12 questions disponible, mais non validé par un juriste. |
| Qualité des agents | Agents juridiques, d'audit et institutionnel disponibles séparément ; pertinence des analyses à évaluer par des spécialistes. |
| Analyse des lacunes et coordination | Policy de provenance et scénarios séquentiels disponibles ; analyse interinstitutionnelle, coordination autonome et arbitrage à construire. |
| Auditabilité | Citations, rapports de scénario et journal JSONL disponibles en CLI ; le raisonnement interne du modèle n'est pas exposé. |
| Alignement architectural | ITU-T Y.3172 et le cadre de préparation à l'IA de l'ITU servent de références de conception ; aucune conformité n'est revendiquée. |

## Architecture et parcours actuel

Le schéma ci-dessous présente le parcours visé. L'index et les premières étapes de recherche et de revue sont implémentés ; l'orchestration multi-agent avec arbitrage est encore une cible.

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
        Recherche et agents spécialisés
        (orchestration complète : cible)
                             |
         Scénarios progressifs (CLI disponible)
                             |
                             v
 Rapport d'audit, références, lacunes et validation humaine
                            |
                            v
       Journal CLI et traces vérifiables
```

### Déposer un dossier confidentiel

L'interface web de démonstration accepte des PDF (y compris les scans si Tesseract est disponible) et des fichiers DOCX. Elle est configurée pour écouter uniquement sur `127.0.0.1`, avec la télémétrie Streamlit désactivée. Les fichiers sont traités en mémoire, dans les limites documentées par l'interface ; leur texte n'est pas ajouté à l'index des sources juridiques. Si l'analyse Ollama, activée par défaut, trouve des sources et lance une génération, le serveur configuré peut recevoir la question, les noms de fichiers, les faits et éléments attendus ainsi que les extraits juridiques retrouvés — pas le texte intégral des documents déposés. Vérifier `CONCORDIA_OLLAMA_BASE_URL` avant usage. Aucun autre traitement cloud n'est configuré dans cette version.

```bash
streamlit run src/web_app.py
```

Le réviseur saisit les questions de contrôle et les éléments attendus ; Concordia vérifie leur présence par correspondance lexicale et retrouve les sources juridiques dans l'index existant. L'option « Rédiger une analyse avec le modèle Ollama configuré » est activée par défaut ; si des sources sont retrouvées et que la génération est lancée, le serveur configuré peut recevoir la question, les noms de fichiers, les faits et éléments attendus, ainsi que les extraits retrouvés, mais pas le texte intégral des documents déposés. Vérifier `CONCORDIA_OLLAMA_BASE_URL` avant de l'activer : l'adresse par défaut est locale, mais elle peut être configurée autrement. Cette première tranche ne détermine pas les obligations applicables, l'authenticité ou la validité des pièces ; aucun référentiel d'audit RCCM juridiquement validé n'est encore fourni. Les résultats restent en mémoire, ne sont pas enregistrés automatiquement et leur téléchargement exige une confirmation à chaque audit. L'interface demande à chaque audit si les originaux doivent rester en mémoire durant la session ou être supprimés ; un bouton permet aussi d'effacer le rapport et l'état de session. N'exposer cette interface sur un réseau ou un serveur distant qu'après avoir défini une politique de sécurité et de conservation adaptée : les fichiers envoyés à une instance distante transiteraient vers cette instance.

Cette architecture reprend le parcours présenté pour le projet : **documents sources → base de connaissances utilisable par les modèles → application de démonstration**. L'objectif est de construire une base réellement interrogeable par les agents, et non de simplement stocker ou citer des documents.

| Étape cible | Rôle dans Concordia | État actuel |
|---|---|---|
| Sources (SRC) | Documents publics et documents métier autorisés, avec juridiction, date, provenance et licence | Des PDF juridiques sont présents localement ; le corpus doit être étendu et sa provenance documentée |
| Collecte et prétraitement (C/PP) | Extraction PDF, OCR si nécessaire, normalisation et segmentation | Pipelines PDF et CCJA disponibles |
| Base de connaissances | Index plein texte et vectoriel, métadonnées, références et relations CCJA | Index SQLite FTS5 ; la recherche juridique privilégie par défaut les textes et exclut la doctrine/manuels et les arrêts CCJA ; embeddings multilingues optionnels |
| Modèles et agents (M) | Recherche fondée sur les sources, analyse documentaire et rôles spécialisés | Agent juridique, agent d'audit documentaire et agent institutionnel ; rédaction Ollama activée par défaut en CLI |
| Politique et coordination | Contrôles de provenance, mandats, protocole d'échange et désaccords entre agents | Première Policy déterministe : vérification exacte des passages/citations indexés et revue humaine obligatoire ; orchestration multi-agent et arbitrage à construire |
| Scénarios et application | Événements publiés progressivement et restitution | Scénarios JSON via CLI et première interface web locale avec dépôt confidentiel de PDF/DOCX |
| Audit et supervision | Sources citées, résultats observables, limites, validation humaine et journal | Rapport JSON/Markdown et journal JSONL local ; revue humaine requise |

### Alignement avec ITU-T Y.3172

Concordia prend **ITU-T Y.3172** (*Architectural overview of machine learning in future networks including IMT-2020*) comme référence d'architecture pour structurer le cycle allant des sources et du prétraitement aux modèles, à leur utilisation et au suivi. La correspondance détaillée entre les composants de la norme et l'implémentation Concordia reste à préciser et à valider au fur et à mesure du développement. Cet alignement est un objectif de conception, pas une conformité déjà démontrée.

Le projet entend également prendre en compte les perspectives du [ITU AI Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf), notamment l'ouverture et la gouvernance des données, l'adaptation au contexte local, l'inclusion, la supervision humaine et les contraintes d'infrastructure.

## Agents disponibles et orchestration cible

Les agents sont des composants documentaires, pas encore une équipe autonome coordonnée de bout en bout :

- **Agent juridique** : recherche des passages et références ; la Policy vérifie leur provenance, pas leur interprétation juridique.
- **Agent d'audit** : compare les éléments attendus aux pièces déclarées et transmet le contexte d'analyse ; il ne prononce pas une conformité.
- **Agent institutionnel** : fournit une perspective à partir d'une institution, d'un mandat et d'une juridiction explicitement donnés via `route --intent institutional_analysis`. Il ne représente aucune position officielle.
- **Orchestrateur actuel** : traite séquentiellement les événements d'un scénario et assemble rapports et journaux. La délégation autonome entre agents, la résolution des désaccords et l'arbitrage sont à construire.

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

## Parcours de démonstration et limites

Le scénario CLI disponible transmet un dossier puis une pièce complémentaire. Il permet de montrer le traitement séquentiel d'informations incomplètes ; il ne démontre pas encore une coordination autonome multi-agent. Un rapport utile doit distinguer :

1. les faits et pièces reçus ;
2. les règles et documents retrouvés, avec leurs références ;
3. les analyses produites par chaque rôle ;
4. les convergences, désaccords, lacunes et points non vérifiés ;
5. les recommandations ou actions proposées, avec les limites et la validation humaine requise.

Les scénarios et résultats devront être évalués sur des cas représentatifs, sans présenter les sorties du prototype comme des décisions juridiques définitives.

### Brouillon de préparation comptable

L'interface web propose un catalogue indicatif de préparation pour une revue comptable, organisé par rubriques de pièces et contrôles documentaires. Le modèle est enregistré dans [`data/checklists/accounting_readiness_draft.json`](data/checklists/accounting_readiness_draft.json) : ses huit contrôles portent chacun leur statut, leur base déclarée et leurs références juridiques. À ce jour, ils sont tous `indicative` et aucune référence officielle n'est associée. Le modèle s'inspire des catégories du texte commercial partagé, mais n'en reprend ni les seuils ni les affirmations juridiques. Il n'est ni exhaustif ni validé juridiquement : les rubriques sélectionnées doivent être adaptées au mandat et vérifiées par un professionnel. Les recherches lexicales de pièces ne déterminent pas leur authenticité, suffisance ou conformité.

Un futur contrôle `expert_validated` doit consigner le réviseur, la date de revue et, pour chaque référence, l'autorité, la citation, la juridiction, une URL, l'identifiant et la section du corpus, le fichier source, son empreinte SHA-256, la version/statut et la personne/date de vérification de son caractère officiel. Le chargeur refuse les entrées incomplètes ou incohérentes et le rapport conserve les métadonnées des contrôles utilisés. Ces champs apportent une piste d'audit, mais le logiciel ne peut pas prouver que les déclarations de revue, l'URL ou le statut juridique sont véridiques : une validation humaine reste indispensable.

## État des lieux du dépôt

### Fonctionnalités disponibles

- [`src/ingestion/ingest.py`](src/ingestion/ingest.py) : extraction et segmentation de PDF juridiques ; les sorties JSON sont nommées à partir de l'empreinte du fichier. À la relance, un PDF inchangé dont la sortie est valide est ignoré ; un PDF modifié ou une sortie absente ou invalide entraîne un nouveau traitement.
- [`src/ingestion/ingest_ccja.py`](src/ingestion/ingest_ccja.py) : conversion d'un corpus CCJA CSV en documents JSONL et en segments de recherche ; rattachement facultatif de relations déjà présentes dans des fichiers CSV du graphe.
- [`src/knowledge/index.py`](src/knowledge/index.py) : construction d'un index local SQLite FTS5, recherche plein texte en français, citations par article/page et chargement des relations CCJA.
- [`src/agents/legal_policy_agent.py`](src/agents/legal_policy_agent.py), [`src/agents/auditor_agent.py`](src/agents/auditor_agent.py) et [`src/agents/institutional_agent.py`](src/agents/institutional_agent.py) : recherche sourcée, identification des pièces manquantes et perspective institutionnelle configurée, sans conclusion automatique de conformité.
- [`src/orchestrator/coordinator.py`](src/orchestrator/coordinator.py) : traitement séquentiel des événements et production d'un rapport ainsi que d'un journal d'audit JSONL.
- [`src/app.py`](src/app.py) : commandes CLI pour créer l'index, poser une question, lancer un audit et consulter des relations CCJA.
- [`src/web_app.py`](src/web_app.py) et [`src/web/audit_workflow.py`](src/web/audit_workflow.py) : interface locale et workflow de revue ; les pièces sont extraites en mémoire et ne sont pas indexées dans le corpus juridique. Le texte intégral des pièces n'est pas envoyé à Ollama, mais les questions, faits, éléments attendus, noms de fichiers et extraits juridiques peuvent l'être si la génération est lancée.
- [`requirements.txt`](requirements.txt) : dépendances du projet.

### À construire ou à valider

- évaluation comparative FTS/vectoriel/hybride sur un benchmark plus large relu par des spécialistes ;
- évaluation experte des synthèses Ollama/RAG et qualité juridique des citations ;
- ingestion complète et documentée des sources nationales et régionales pertinentes ;
- corpus réglementaire institutionnel dédié, mandats documentés, arbitrage et protocole d'échange multi-acteurs ;
- amélioration de l'interface et de la supervision humaine interactive ;
- validation juridique et métier du rapport sur des scénarios réalistes ;
- tests de qualité de recherche, de conformité des réponses, de robustesse et de performance ;
- coordination multi-agent, désaccords et arbitrage, au-delà de l'exécution séquentielle actuelle.

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

Le modèle par défaut est un choix de démarrage léger, pas une recommandation pour prendre des décisions juridiques. Les commandes `ask`, `route` et `audit` utilisent Ollama par défaut pour rédiger une réponse narrative à partir des passages retrouvés ; `--extractive` affiche uniquement les extraits. Ollama ne reçoit pas de contexte juridique en l'absence de passage retrouvé. Les sorties générées sont rattachées aux sources fournies et vérifiées par Policy, mais ce contrôle vérifie la provenance, pas le raisonnement juridique ; une revue humaine reste obligatoire.

Installer et lancer Ollama, puis télécharger le modèle :

```bash
ollama pull qwen2.5:3b
```

La synthèse est activée par défaut. Pour demander explicitement une réponse extractive sans appel Ollama :

```bash
python -m src.app ask "Quel texte porte le Code électoral camerounais ?" --extractive
python -m src.app route "Quels articles parlent de l'immatriculation ?" --extractive
```

## Données et provenance

Les scripts d'ingestion utilisent les chemins suivants par défaut :

- PDF juridiques : `data/raw_legal_docs/` ;
- corpus CCJA : `data/knowledge_graphs/ccja_jurisprudence/ccja_corpus/full_dataset.csv` ;
- relations CCJA : `data/knowledge_graphs/ccja_jurisprudence/ccja_corpus/ohada_graph/` ;
- documents et segments JSON/JSONL : `02_PROCESSED_JSON/`.

Le corpus CCJA est traité séparément des PDF. L'indexeur inclut les décisions, leurs segments et les relations disponibles dans les JSONL. La construction produit un index SQLite local avec recherche plein texte et graphe documentaire ; les embeddings sont une étape optionnelle distincte. Il ne s'agit pas d'une base distribuée.

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

La commande `ask` limite par défaut les résultats aux textes juridiques : les décisions CCJA et les documents classés comme doctrine/manuels ne sont pas mélangés à ces résultats. La recherche plein texte classe les candidats selon la couverture des termes significatifs et leur proximité ; si les termes centraux ne concordent pas, elle s'abstient au lieu de présenter des passages trouvés sur de simples mots génériques. Pour les questions qui exigent une correspondance sémantique ou des formulations différentes, construire l'index vectoriel puis choisir le mode hybride. Pour une recherche de jurisprudence ou de doctrine, utiliser `--source-scope case_law` ou `--source-scope doctrine`. L'option `--include-doctrine` conserve les textes juridiques dans leur rubrique et ajoute séparément un éclairage doctrinal ; dans les audits, cet éclairage apparaît aussi distinctement comme piste à examiner. La doctrine n'est jamais présentée comme preuve d'une obligation et n'alimente pas les affirmations juridiques générées par Ollama. `--source-scope all` reste disponible pour consulter explicitement tous les corpus. Ces filtres s'appliquent aussi aux modes vectoriel et hybride et ne nécessitent pas de reconstruire l'index existant.

```bash
python -m src.app ask "Immatriculation au RCCM" --source-scope case_law
python -m src.app ask "Immatriculation au RCCM" --source-scope doctrine
python -m src.app ask "Immatriculation au RCCM" --include-doctrine
python -m src.app ask "Immatriculation au RCCM" --source-scope all
```

Par défaut, Ollama rédige une réponse en français à partir des seuls passages retenus par la recherche ; Concordia restitue les citations correspondantes. Avec `--extractive`, la commande n'appelle pas Ollama et affiche les extraits. Si aucun passage pertinent n'est retenu, aucune génération n'est lancée. Le contrôle Policy vérifie la présence des sources dans l'index, pas que le raisonnement est juridiquement exact ; la revue humaine reste nécessaire.

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

Le scénario d'exemple transmet un dossier initial, puis une pièce complémentaire. Les événements sont évalués dans l'ordre ; les pièces manquantes sont celles déclarées par le scénario, et non une conclusion de non-conformité légale. En CLI, Ollama rédige si des sources ont été retrouvées une analyse à partir de la question, des faits, des pièces déclarées et des éléments attendus. Le rendu Markdown suit un template stable : contrôle, analyse assistée à valider, pièces manquantes, sources juridiques, éclairage doctrinal séparé, incertitudes et prochaines étapes. `--extractive` désactive la génération. Le rapport JSON et son journal JSONL sont écrits localement dans `data/audits/`.

### Consulter les relations CCJA indexées

```bash
python -m src.app graph OHADA-CCJA-00000
```

Ces relations sont celles présentes dans le corpus importé ; elles ne sont pas une interprétation juridique autonome.

La reconstruction de l'index crée aussi un graphe documentaire local : documents, sections, hiérarchie des titres et références explicites entre articles d'un même document. La recherche peut compléter un résultat principal par les articles qu'il cite lorsque la liste de résultats n'est pas déjà remplie. Ce graphe ne déduit pas de relations juridiques absentes du texte.

```bash
python -m src.app build-index
python -m src.app graph-neighbors ohada-acte-uniforme-2010-droit-commercial-c554eccc \
  --section-id ohada-acte-uniforme-2010-droit-commercial-c554eccc-livre-2-titre-2-chapitre-1-section-2-article-47
```

Après une mise à jour du code, relancer `build-index` pour créer le graphe dans la base locale existante.

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

**Team leader :** BOKOU-BOUNA-ANGE-LARISSA — University of Yaoundé I, Cameroon

**Contact :** [larissa.bokou@facsciences-uy1.cm](mailto:larissa.bokou@facsciences-uy1.cm)

**Membres**
- NANGMO FEULFACK ANNICK — Member 2 — [duplusse.nangmo@facsciences-uy1.cm](mailto:duplusse.nangmo@facsciences-uy1.cm)
- DJATCHE-NKAMGANG SYLVANO — Member 3 — [sylvano.djatche-nkamgang@facsciences-uy1.cm](mailto:sylvano.djatche-nkamgang@facsciences-uy1.cm)

**Mentor :** Pr Paulin Yonta Melatagia — [paulinyonta@gmail.com](mailto:paulinyonta@gmail.com)

**GitHub :** [Concordia-CM/Concordia](https://github.com/Concordia-CM/Concordia)
