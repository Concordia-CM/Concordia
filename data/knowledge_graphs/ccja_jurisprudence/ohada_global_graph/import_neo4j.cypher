
// ============================================================
// OHADA-CCJA Legal Knowledge Graph — Neo4j Import
// ============================================================

// 1. Create constraints
CREATE CONSTRAINT FOR (c:Case) REQUIRE c.case_id IS UNIQUE;
CREATE CONSTRAINT FOR (d:LegalDomain) REQUIRE d.domain_id IS UNIQUE;
CREATE CONSTRAINT FOR (s:MemberState) REQUIRE s.state_id IS UNIQUE;
CREATE CONSTRAINT FOR (a:ActeUniforme) REQUIRE a.acte_id IS UNIQUE;
CREATE CONSTRAINT FOR (art:Article) REQUIRE art.article_number IS UNIQUE;

// 2. Load Case nodes
LOAD CSV WITH HEADERS FROM 'file:///nodes/cases.csv' AS row
CREATE (c:Case {
  case_id: row.case_id,
  case_number: row.case_number,
  year: toInteger(row.year),
  legal_domain: row.legal_domain,
  source: row.source
});

// 3. Load other nodes
LOAD CSV WITH HEADERS FROM 'file:///nodes/legal_domains.csv' AS row
CREATE (:LegalDomain {domain_id: row.domain_id, name: row.name, case_count: toInteger(row.case_count)});

LOAD CSV WITH HEADERS FROM 'file:///nodes/member_states.csv' AS row
CREATE (:MemberState {state_id: row.state_id, name: row.name});

LOAD CSV WITH HEADERS FROM 'file:///nodes/actes_uniformes.csv' AS row
CREATE (:ActeUniforme {acte_id: row.acte_id, full_name: row.full_name, domain: row.domain});

LOAD CSV WITH HEADERS FROM 'file:///nodes/articles.csv' AS row
CREATE (:Article {article_number: toInteger(row.article_number), article_id: row.article_id});

// 4. Load edges
LOAD CSV WITH HEADERS FROM 'file:///edges/case_cites_case.csv' AS row
WITH row WHERE row.cited_case_id IS NOT NULL
MATCH (a:Case {case_id: row.source_case_id})
MATCH (b:Case {case_id: row.cited_case_id})
CREATE (a)-[:CITES]->(b);

LOAD CSV WITH HEADERS FROM 'file:///edges/case_classified_as_domain.csv' AS row
MATCH (c:Case {case_id: row.case_id})
MATCH (d:LegalDomain {domain_id: row.domain_id})
CREATE (c)-[:CLASSIFIED_AS]->(d);

LOAD CSV WITH HEADERS FROM 'file:///edges/case_originates_from_state.csv' AS row
MATCH (c:Case {case_id: row.case_id})
MATCH (s:MemberState {state_id: row.state_id})
CREATE (c)-[:ORIGINATES_FROM]->(s);

LOAD CSV WITH HEADERS FROM 'file:///edges/case_references_acte.csv' AS row
MATCH (c:Case {case_id: row.case_id})
MATCH (a:ActeUniforme {acte_id: row.acte_id})
CREATE (c)-[:REFERENCES]->(a);

LOAD CSV WITH HEADERS FROM 'file:///edges/case_cites_article.csv' AS row
MATCH (c:Case {case_id: row.case_id})
MATCH (a:Article {article_number: toInteger(row.article_number)})
CREATE (c)-[:CITES_ARTICLE]->(a);
