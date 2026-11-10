# Concordia

**A prototype for legal research and compliance review in the OHADA-CEMAC region, starting with Cameroon.**

Concordia is a prototype developed for the **AI for Good Sandbox Hackathon – United Arab Emirates**, organized by the ITU AI for Good Lab. It explores how a sourced legal and policy knowledge base can support domain-focused analysis and produce verifiable findings. Its legal scope remains OHADA-CEMAC, starting with Cameroon; policy-gap analysis focuses on domain-level issues rather than geographic comparisons or country-specific recommendations, and searches for relevant global examples in the knowledge base.

> **Demonstration prototype — not legal advice.** Document retrieval, Ollama responses grounded in retrieved passages, CLI audit scenarios, and a local PDF/DOCX review interface are available. Full multi-agent coordination, legally validated audit frameworks, and expert evaluation remain to be developed. The prototype does not certify compliance and does not demonstrate compliance with ITU-T Y.3172.

## Project at a glance

**The problem.** A compliance review must connect case facts and documents to laws and regulations from different jurisdictions and domains, while preserving the sources of each rule and making uncertainty visible.

**The approach.** Concordia indexes legal documents, retrieves passages with citations, and can ask the configured Ollama model to draft an answer limited to those passages. In an audit scenario, the system distinguishes reported facts, expected documents, and legal references; a human remains responsible for the final decision.

**What can be demonstrated today**

- Local, cited search with separate scopes for legal texts, CCJA case law, and doctrine.
- Ollama-generated narrative answers based on retrieved sources, or extractive results without generation.
- Sequential CLI audit scenarios and local PDF/DOCX document review.
- An experimental Web workflow for classifying domain-level policy gaps and retrieving sources.
- Citation provenance checks, with results marked as requiring human review.

**What has not yet been demonstrated.** Fully coordinated agents with arbitration, the legal relevance of generated answers, the validity of submitted documents, and compliance with an audit framework all require specialist evaluation. The retrieval benchmark is an initial test set, not legal validation.

**Quick try** (after installation and index preparation, described below):

```bash
# Ask a question without generation
python -m src.app ask "Quelles dispositions concernent l'immatriculation au RCCM ?" --extractive

# Open the local document review interface
streamlit run src/web_app.py

# Evaluate retrieval on the reference set
python -m src.app evaluate-search data/evaluation/legal_retrieval.json --top-k 5
```

The Web workflow does not send the full text of uploaded files to Ollama. If generation is enabled and relevant sources are found, the configured Ollama server may receive the question, policy domain and issue, file names, reported facts, expected evidence, and retrieved legal excerpts. Check `CONCORDIA_OLLAMA_BASE_URL` before testing.

**Explore further:** [architecture and current status](#architecture-and-current-workflow) · [agents and limitations](#available-agents-and-target-orchestration) · [installation and commands](#installation) · [retrieval evaluation](#evaluate-document-retrieval) · [data and provenance](#data-and-provenance).

## Hackathon context

The hackathon aims to create an open infrastructure for knowledge and AI agents operating in practical domains while taking policies, laws, and institutional responsibilities into account. It encourages:

- Knowledge bases grounded in properly sourced national public documents.
- Specialized agents, such as legal or policy advisers, institutional representatives, and application agents.
- Realistic simulations with partial information distributed over time.
- Coordination between agents with distinct roles and mandates.
- Audit logs and verifiable justification traces, including consulted references, steps, decisions, and agent outputs.
- Analysis of policy, regulatory, standards, and coordination gaps informed by relevant international examples.

Concordia applies this approach to legal, tax, and banking policy questions in the OHADA-CEMAC scope, beginning with Cameroon. Its current source base is primarily OHADA/CCJA and Cameroon-related material. The analysis focuses on domain-level gaps—such as unclear responsibilities, missing standards, technology limitations, legislative gaps, coordination failures, or conflicting objectives—and searches the index for relevant international policies, frameworks, and standards as comparators. Results remain constrained by the coverage of the indexed corpus; the geographic coverage of that corpus is not the intended focus of recommendations.

The official page describes the evaluation criteria and expected deliverables: [AI for Good Sandbox Hackathon – United Arab Emirates](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/).

## Problem and proposal

Audit and compliance teams must compare documents with different scopes and legal authority: statutes, sector regulations, institutional rules, policies, and procedures. A useful answer must do more than find a potentially relevant rule: it should explain its basis, flag uncertainty, and let a human verify the sources.

Concordia aims to turn these sources into a knowledge base that specialized agents can use. Today, users can submit a question or run a sequential scenario. The longer-term goal is for coordinated agents to compare their analyses against sources and produce a traceable report for human review.

Results are intended to support analysis; they do not replace professional legal advice or a decision by a competent authority.

## Target success criteria

The hackathon highlights several areas. The table distinguishes what can currently be observed from what still needs validation:

| Evaluation criterion | Current status and remaining gap |
|---|---|
| Knowledge-base quality and provenance | A local searchable index carries document and section references. Coverage, currency, metadata completeness, and extraction accuracy still need expert review; the 12-question retrieval benchmark is not legal validation. |
| Agent capability | Search, document-audit, and institutional components can return sourced results. Scenario-based tests and expert evaluation of relevance, correctness, mandates, and coordination remain necessary. |
| Domain-level policy gaps and global examples | The experimental Web workflow structures gaps by responsibility, policy/strategy, standards, technology, legislation, coordination, and conflicting objectives, and searches the index using international comparison terms. Indexed sources are mainly OHADA/CCJA and Cameroon-related, so global comparisons remain limited by current corpus coverage. Do not treat retrieved local/regional law as a global comparator or produce country-specific recommendations. |
| Auditability | The Web report records observable inputs, retrieval steps, policy outcomes, and source identifiers/citations. It does not expose or claim to expose an LLM chain of thought. |
| ITU alignment | ITU-T Y.3172 and the ITU AI Readiness Framework are design references. A detailed, tested mapping to their components is still required; no standards-compliance claim is made. |

## Architecture and current workflow

The diagram shows the intended workflow. The index and initial search and review stages are implemented; full multi-agent orchestration, arbitration, and a validated global policy corpus remain targets.

```text
Statutes, regulations, decisions, policies, and business documents
                            |
                            v
       Collection, OCR, extraction, and normalization
                            |
                            v
    Versioned, sourced, searchable knowledge base
              (search/RAG index and relations)
                            |
                            v
             Search and specialized agents
              (full orchestration: target)
                            |
          Progressive scenarios (CLI available)
                            |
                            v
 Audit report, references, gaps, and human review
                            |
                            v
       CLI log and verifiable execution traces
```

### Reviewing a confidential case file

The demonstration web interface accepts PDF files (including scanned PDFs if Tesseract is available) and DOCX files. It listens on `127.0.0.1`, with Streamlit telemetry disabled. Files are processed in memory within the documented limits; their text is not added to the legal-source index. If Ollama analysis is enabled and a source is found, the configured server may receive the question, file names, reported facts, expected evidence, and retrieved legal excerpts—but not the full text of uploaded documents. Check `CONCORDIA_OLLAMA_BASE_URL` before use. No other cloud processing is configured.

```bash
streamlit run src/web_app.py
```

The reviewer enters control questions and expected evidence. Concordia checks for their presence using lexical matching and retrieves legal sources from the existing index. The “Draft an analysis with the configured Ollama model” option is enabled by default; if sources are found and generation runs, the configured server may receive the question, file names, reported facts, expected evidence, and retrieved excerpts, but not the full text of uploaded documents. Check `CONCORDIA_OLLAMA_BASE_URL` before enabling it; the default address is local, but it can be changed. This initial implementation does not determine applicable obligations or establish the authenticity or validity of submitted documents. No legally validated RCCM audit framework is provided.

The **Policy gap analysis by domain** workflow structures a thematic query across responsibilities and mandates, policies and strategies, standards, technology, legislation, coordination, and conflicting objectives. It searches the existing index for domain sources and separately searches records explicitly tagged with global/international geographic scope for policy, framework, or standards comparators. Retrieved passages are shown with their indexed domain and file provenance; local/regional texts are not treated as global comparators, and the workflow does not generate country-specific recommendations. The current corpus contains no such globally tagged comparators, so international comparison results depend on future expansion of the indexed collection.

Reports remain in memory and are not saved automatically; downloading requires confirmation. The interface lets the reviewer choose whether uploaded originals remain in memory for the session or are cleared after review, and provides a control to clear the report and session state. Do not expose the interface on a network or remote server without an appropriate security and retention policy: files uploaded to a remote instance would be transmitted to that instance.

This architecture follows the project path: **source documents → knowledge base usable by models → demonstration application**. The goal is to make the sources searchable by agents, not merely to store or cite documents.

| Target stage | Role in Concordia | Current status |
|---|---|---|
| Sources (SRC) | Authorized public and business documents with jurisdiction, date, provenance, and license | Legal PDFs are available locally; the corpus needs to be expanded and its provenance documented. |
| Collection and preprocessing (C/PP) | PDF extraction, OCR where needed, normalization, and chunking | PDF and CCJA pipelines are available. |
| Knowledge base | Full-text and vector indexes, metadata, references, and CCJA relations | SQLite FTS5 index; legal-text search excludes doctrine/manuals and CCJA decisions by default; multilingual embeddings are optional. |
| Models and agents (M) | Source-grounded search, document analysis, and specialized roles | Legal, document-audit, and institutional agents; Ollama generation is enabled by default in the CLI. |
| Policy and coordination | Provenance controls, mandates, exchange protocol, and agent disagreements | Initial deterministic Policy verifies that passages/citations exist in the index and requires human review; multi-agent orchestration and arbitration remain to be built. |
| Domain-level gap analysis | Identify unclear roles, missing standards, technology/legal gaps, coordination failures, and competing objectives; compare with global policy examples | The Web workflow structures these gap categories and searches the current index. Global source coverage and metadata are not yet sufficient for validated comparisons. |
| Scenarios and application | Progressive events and results | JSON scenarios via CLI and an initial local web interface for confidential PDF/DOCX uploads. |
| Audit and oversight | Cited sources, observable results, limitations, human review, and logging | JSON/Markdown reports and a local JSONL log; human review is required. |

### Alignment with ITU-T Y.3172

Concordia uses **ITU-T Y.3172** (*Architectural overview of machine learning in future networks including IMT-2020*) as an architectural reference for structuring the lifecycle from sources and preprocessing through models, deployment, and monitoring. The detailed mapping between the recommendation and the implementation remains to be specified and validated. This is a design goal, not a demonstrated compliance claim.

The project also intends to consider the [ITU AI Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf), including data openness and governance, local adaptation, inclusion, human oversight, and infrastructure constraints.

## Available agents and target orchestration

The agents are document-analysis components, not yet an autonomous team coordinated end to end:

- **Legal agent:** retrieves passages and references. Policy checks their provenance, not their legal interpretation.
- **Audit agent:** compares expected evidence with declared documents and passes analysis context; it does not determine compliance.
- **Institutional agent:** provides a perspective based on an explicitly supplied institution, mandate, and jurisdiction via `route --intent institutional_analysis`. It does not represent an official position.
- **Current orchestrator:** processes scenario events sequentially and assembles reports and logs. Autonomous delegation, disagreement resolution, and arbitration remain to be built.

Institutional analysis can be run directly:

```bash
python -m src.app route "Examiner les obligations de déclaration" \
  --intent institutional_analysis \
  --institution "Autorité de supervision" \
  --mandate "Examiner les obligations de déclaration" \
  --jurisdiction "Cameroun"
```

It can also be enabled in an audit scenario by adding an optional root-level configuration:

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

The orchestrator applies this perspective to each control, then adds the result, references, and Policy decision to the report and audit log. `generate` is disabled by default; enabling it requires a configured Ollama server. Institutional analysis currently searches the same general document index as the legal agent; there is no dedicated institutional corpus yet.

The hackathon calls for audit logs and reasoning traces. The prototype records observable events, checks, and retrieved references; it does not expose or claim to expose a model's internal chain of thought. Traceability relies on verifiable artifacts: source citations and identifiers, agent inputs and outputs, scenario steps, timestamps, Policy outcomes, and human-review decisions.

## Demonstration workflow and limitations

The available CLI scenario provides an initial case file, followed by a supplementary document. It demonstrates sequential processing of incomplete information; it does not yet demonstrate autonomous multi-agent coordination. A useful report should distinguish:

1. Facts and documents received.
2. Retrieved rules and documents, with references.
3. Analyses produced by each role.
4. Agreements, disagreements, gaps, and unverified points.
5. Recommendations or proposed actions, with limitations and required human review.

Scenarios and results must be evaluated on representative cases. Prototype outputs must not be presented as definitive legal decisions.

### Accounting-readiness draft

The web interface offers an indicative accounting-review preparation catalog, organized by document categories and documentary controls. The model is stored in [`data/checklists/accounting_readiness_draft.json`](data/checklists/accounting_readiness_draft.json). Each of its eight controls has a status, stated basis, and legal-reference fields. All controls are currently `indicative`, and no official legal sources are associated with them. The draft is inspired by categories in a shared business document, but does not reproduce its thresholds or legal claims. It is not exhaustive or legally validated; selected categories must be adapted to the engagement and reviewed by a professional. Lexical document checks do not determine authenticity, sufficiency, or compliance.

A future `expert_validated` control must record the reviewer and review date, and for each reference the authority, citation, jurisdiction, URL, corpus record and section IDs, source file, SHA-256 hash, version/status, and who verified its official status and when. The loader rejects incomplete or inconsistent entries, and the report retains metadata for the controls used. These fields provide an audit trail, but the software cannot prove that review statements, URLs, or legal-status claims are true; human validation remains essential.

## Repository status

### Available functionality

- [`src/ingestion/ingest.py`](src/ingestion/ingest.py): extracts and chunks legal PDFs. Output JSON files are named using the source file hash. On rerun, an unchanged PDF with a valid output is skipped; a modified PDF or missing/invalid output is processed again.
- [`src/ingestion/ingest_ccja.py`](src/ingestion/ingest_ccja.py): converts a CCJA CSV corpus into JSONL documents and search chunks; can optionally attach relations already present in graph CSV files.
- [`src/knowledge/index.py`](src/knowledge/index.py): builds a local SQLite FTS5 index, supports French full-text search and article/page citations, and loads CCJA relations.
- [`src/agents/legal_policy_agent.py`](src/agents/legal_policy_agent.py), [`src/agents/auditor_agent.py`](src/agents/auditor_agent.py), and [`src/agents/institutional_agent.py`](src/agents/institutional_agent.py): provide sourced search, identification of missing documents, and configured institutional perspectives without automatically determining compliance.
- [`src/orchestrator/coordinator.py`](src/orchestrator/coordinator.py): processes scenario events sequentially and produces a report and JSONL audit log.
- [`src/app.py`](src/app.py): CLI commands to build the index, ask a question, run an audit, and inspect CCJA relations.
- [`src/web_app.py`](src/web_app.py), [`src/web/audit_workflow.py`](src/web/audit_workflow.py), and [`src/web/policy_gap_workflow.py`](src/web/policy_gap_workflow.py): local document-review and experimental domain-level policy-gap workflows. Uploaded files are extracted in memory and are not indexed in the legal corpus. If generation runs, the configured Ollama server may receive questions, analysis context, file names, facts, expected evidence, and retrieved excerpts—but not the full text of uploaded files.
- [`requirements.txt`](requirements.txt): project dependencies.

### To build or validate

- Compare FTS, vector, and hybrid retrieval on a larger benchmark reviewed by specialists.
- Obtain expert evaluation of Ollama/RAG summaries and citation quality.
- Ingest and document a more complete set of relevant national and regional sources.
- Add well-sourced, expert-validated global policy examples with provenance and scope metadata.
- Evaluate domain-level gap analyses and global comparisons against expert-reviewed cases.
- Build a dedicated institutional regulatory corpus, document mandates, and implement multi-party exchange and arbitration.
- Add and validate globally relevant policy sources with jurisdiction/scope, publisher, date/version, URL, license, and provenance metadata; evaluate cross-domain comparisons against expert-reviewed examples.
- Improve the interface and interactive human oversight.
- Validate the report against realistic legal and business scenarios.
- Test retrieval quality, response provenance, robustness, and performance.
- Implement multi-agent coordination, disagreement handling, and arbitration beyond the current sequential workflow.

The `src/policy/` directory contains an initial provenance Policy in `src/policy/legal_policy.py`. It blocks missing or falsified references and requires human review for other outputs; it does not verify legal scope or hierarchy. Shared contracts and an optional Ollama client are available. The institutional agent can be routed directly or included in an audit scenario, but it searches the same general index because no dedicated corpus exists. Multi-agent coordination with arbitration remains to be built.

### Configuration and Ollama

Configuration is read from environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `CONCORDIA_DATABASE_PATH` | `data/knowledge_base/concordia.sqlite3` | Local database path |
| `CONCORDIA_EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Embedding model |
| `CONCORDIA_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `CONCORDIA_OLLAMA_MODEL` | `qwen2.5:3b` | Local Ollama generation model; set the variable to an empty value to disable it |
| `CONCORDIA_LLM_TIMEOUT_SECONDS` | `120` | Timeout for generation requests |

The default model is a lightweight starting choice, not a recommendation for legal decision-making. The `ask`, `route`, and `audit` commands use Ollama by default to draft narrative answers from retrieved passages; `--extractive` displays only excerpts. Ollama receives no legal context when no passage is retrieved. Generated claims are linked to supplied sources and checked by Policy, but this checks provenance, not legal reasoning; human review remains required.

Install and start Ollama, then download the model:

```bash
ollama pull qwen2.5:3b
```

Generation is enabled by default. To explicitly request an extractive answer without calling Ollama:

```bash
python -m src.app ask "Quel texte porte le Code électoral camerounais ?" --extractive
python -m src.app route "Quels articles parlent de l'immatriculation ?" --extractive
```

## Data and provenance

The ingestion scripts use these default paths:

- Legal PDFs: `data/raw_legal_docs/`
- CCJA corpus: `data/knowledge_graphs/ccja_jurisprudence/ccja_corpus/full_dataset.csv`
- CCJA relations: `data/knowledge_graphs/ccja_jurisprudence/ccja_corpus/ohada_graph/`
- Processed JSON/JSONL documents and chunks: `02_PROCESSED_JSON/`

The CCJA corpus is processed separately from PDFs. The indexer includes decisions, their chunks, and relations available in JSONL. Building the index creates a local SQLite full-text index and document graph; embeddings are a separate optional step. This is not a distributed database.

For each dataset published or shared, document at least the source organization, URL or reference, jurisdiction, geographic scope, date/version, license, and transformations applied. Global-policy records must declare a `geographic_scope`, `jurisdiction`, or `scope` metadata value of `global`, `international`, `worldwide`, or `multilateral` to be included in the comparative search. Check reuse and redistribution rights before publishing documents or derived results. Locally generated outputs are not necessarily included in Git.

## Installation

Requirements: Python 3.10 or later. To OCR scanned PDFs on Ubuntu, also install Tesseract and the French language data:

```bash
sudo apt install tesseract-ocr tesseract-ocr-fra
```

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

Run the PDF ingestion pipeline from the repository root:

```bash
python -m src.ingestion.ingest
```

The pipeline scans `data/raw_legal_docs/` and writes one JSON file per processed PDF to `02_PROCESSED_JSON/`. Unchanged documents that have already been processed are skipped on subsequent runs.

Import the CCJA corpus using the default paths:

```bash
python -m src.ingestion.ingest_ccja
```

The default output files are:

- `02_PROCESSED_JSON/ccja-decisions.jsonl`: one normalized decision per line.
- `02_PROCESSED_JSON/ccja-search-chunks.jsonl`: text chunks associated with a decision and source field.

Use `--csv`, `--graph-dir`, `--output`, `--chunks-output`, `--chunk-size`, and `--chunk-overlap` to customize paths and chunking. See the command help:

```bash
python -m src.ingestion.ingest_ccja --help
```

### Build or update the knowledge base

From the repository root, after producing JSON and JSONL documents:

```bash
python -m src.app build-index
```

This indexes JSON files in `02_PROCESSED_JSON/` and CCJA decisions and chunks, if present. The SQLite index is created locally at `data/knowledge_base/concordia.sqlite3` and is not committed to Git. Each rebuild replaces the index contents with the files present at that time.

### Ask a documentary question

```bash
python -m src.app ask "Quelles dispositions concernent l'immatriculation au RCCM ?"
```

The `ask` command searches legal texts by default; CCJA decisions and documents classified as doctrine/manuals are not mixed into those results. Full-text search ranks candidates by significant-term coverage and proximity. If central terms do not match, it abstains rather than returning passages matching only generic words. For questions requiring semantic matching or different wording, build the vector index and select hybrid mode. Use `--source-scope case_law` or `--source-scope doctrine` to search case law or doctrine. `--include-doctrine` keeps legal texts in their own section and adds doctrinal material separately as non-normative context; audits also show it separately as a research lead. Doctrine is never presented as proof of a legal obligation and is not used to generate legal claims with Ollama. `--source-scope all` is available to search all corpora explicitly. These filters also apply to vector and hybrid modes and do not require rebuilding the index.

```bash
python -m src.app ask "Immatriculation au RCCM" --source-scope case_law
python -m src.app ask "Immatriculation au RCCM" --source-scope doctrine
python -m src.app ask "Immatriculation au RCCM" --include-doctrine
python -m src.app ask "Immatriculation au RCCM" --source-scope all
```

By default, Ollama drafts a French answer based only on passages selected by search; Concordia returns the corresponding citations. With `--extractive`, the command does not call Ollama and displays the excerpts. If no relevant passage is selected, generation is not run. Policy checks that sources exist in the index, not that the reasoning is legally correct; human review remains necessary.

### Route a request

The `route` command deterministically recognizes two available workflows: legal search and document audit. It does not use a model to infer intent; ambiguous or unrecognized requests are rejected rather than routed by default. Use `--intent` to specify the workflow. An audit always requires a JSON scenario:

```bash
python -m src.app route "Quels articles parlent de l'immatriculation ?"
python -m src.app route "Lancer un audit de conformité" --scenario data/scenarios/cameroon_company_document_review.json
python -m src.app route "Auditer ce dossier et rechercher les articles applicables" --intent document_audit --scenario data/scenarios/cameroon_company_document_review.json
```

Automatic intent detection supports only these two workflows. Institutional analysis requires an explicit `--intent institutional_analysis`; generation is an agent option, not a separately routed workflow, and the CLI does not make automated legal decisions.

### Evaluate document retrieval

The benchmark `data/evaluation/legal_retrieval.json` contains 12 documentary-review questions covering RCCM, labor law, consumer protection, credit, competition, and the SYCEBNL accounting framework. Each case specifies a domain, an audit focus, one or more expected references, and sometimes a distractor passage. References were checked against files in the local corpus, but the benchmark has not been reviewed by a legal expert and does not certify the authority or current validity of the cited texts. It measures recall, precision@5, reciprocal rank, citation coverage, and latency; it does not assess legal interpretation or checklist quality. The RCCM question also uses title and section hierarchy to prioritize provisions classified under registration. This ranking signal does not validate whether a provision applies:

```bash
python -m src.app evaluate-search data/evaluation/legal_retrieval.json --top-k 5
```

Evaluation defaults to legal texts, excluding doctrine and CCJA case law; use `--source-scope all` to change the scope. This is an initial FTS benchmark, not proof of general search quality. A legal professional should review the questions, expected references, and distractors before they are used as ground truth. Audit focuses are research prompts, not exhaustive or validated regulatory checklists.

### Enable local vector search

FTS remains the default. To calculate passage vectors locally, install the dependencies and rebuild the index with the multilingual Sentence Transformers model (384 dimensions):

```bash
pip install -r requirements.txt
python -m src.app build-index --vector-model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

The first run downloads the model weights from Hugging Face; document and query encoding then runs on the CPU. Vectors are stored in the local SQLite database. Select the retrieval mode explicitly:

```bash
python -m src.app ask "Quel texte porte le Code électoral camerounais ?" --retrieval-mode fts
python -m src.app ask "Quel identifiant commercial doit apparaître dans un avis publié par une société ?" --retrieval-mode vector
python -m src.app ask "Quel identifiant commercial doit apparaître dans un avis publié par une société ?" --retrieval-mode hybrid
python -m src.app evaluate-search data/evaluation/legal_retrieval.json --retrieval-mode hybrid
```

Hybrid mode combines lexical and vector rankings using Reciprocal Rank Fusion; the raw scores from the two engines are not comparable. Vector search does not generate an answer: results remain cited document excerpts. The local model has not yet been evaluated on a benchmark validated by a lawyer.

### Run a progressive review scenario

```bash
python -m src.app audit data/scenarios/cameroon_company_document_review.json
```

The example scenario provides an initial case file followed by a supplementary document. Events are evaluated in order; missing documents are defined by the scenario and do not establish legal non-compliance. In the CLI, if sources are found, Ollama drafts an analysis from the question, facts, declared documents, and expected evidence. The Markdown report follows a stable template: control, AI-assisted analysis for review, missing documents, legal sources, separate doctrinal context, uncertainties, and next steps. `--extractive` disables generation. The JSON report and JSONL log are written locally to `data/audits/`.

### Inspect indexed CCJA relations

```bash
python -m src.app graph OHADA-CCJA-00000
```

These are relations present in the imported corpus; they are not an independent legal interpretation.

Index reconstruction also creates a local document graph: documents, sections, title hierarchy, and explicit references between articles in the same document. Search may add articles cited by a main result when the result list is not already full. The graph does not infer legal relationships absent from the source text.

```bash
python -m src.app build-index
python -m src.app graph-neighbors ohada-acte-uniforme-2010-droit-commercial-c554eccc \
  --section-id ohada-acte-uniforme-2010-droit-commercial-c554eccc-livre-2-titre-2-chapitre-1-section-2-article-47
```

After updating the code, rerun `build-index` to create the graph in the existing local database.

### Tests

```bash
python -m unittest discover -s tests
```

## Hackathon deliverables

According to the [official hackathon page](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/), submission materials include:

1. A technical report of no more than five pages.
2. The project GitHub repository.
3. A knowledge base containing policies, regulations, and strategies.
4. Optionally, a demonstration video of no more than seven minutes (required for shortlisted teams, according to the page).

The knowledge-base build code, the knowledge base itself, reports, and the demonstration must be prepared and checked before submission. Consult the official page for deadlines, procedures, team rules, and updates.

## References

- [AI for Good Sandbox Hackathon – United Arab Emirates](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/)
- [ITU-T Recommendation Y.3172](https://www.itu.int/rec/T-REC-Y.3172/en)
- [ITU AI Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf)
- [ITU AI for Good Lab](https://aiforgood.itu.int/)

## Team

**Team leader:** BOKOU-BOUNA-ANGE-LARISSA — University of Yaoundé I, Cameroon

**Contact:** [larissa.bokou@facsciences-uy1.cm](mailto:larissa.bokou@facsciences-uy1.cm)

**Members**
- NANGMO FEULFACK ANNICK — Member 2 — [duplusse.nangmo@facsciences-uy1.cm](mailto:duplusse.nangmo@facsciences-uy1.cm)
- DJATCHE-NKAMGANG SYLVANO — Member 3 — [sylvano.djatche-nkamgang@facsciences-uy1.cm](mailto:sylvano.djatche-nkamgang@facsciences-uy1.cm)

**Mentor:** Professor Paulin Yonta Melatagia — [paulinyonta@gmail.com](mailto:paulinyonta@gmail.com)

**GitHub:** [Concordia-CM/Concordia](https://github.com/Concordia-CM/Concordia)
