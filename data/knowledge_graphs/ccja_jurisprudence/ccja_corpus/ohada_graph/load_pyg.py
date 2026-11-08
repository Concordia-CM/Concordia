
import pandas as pd
import torch
from torch_geometric.data import HeteroData
import networkx as nx
import matplotlib.pyplot as plt


def load_ohada_graph(graph_dir='ohada_graph'):
    """
    Load the OHADA-CCJA Legal Knowledge Graph as a PyG HeteroData object.
    
    Node types: case, domain, state, acte, article, party
    Edge types: cites, classified_as, originates_from, references, cites_article, involves
    """
    data = HeteroData()
    
    # Load nodes
    cases = pd.read_csv(f'{graph_dir}/nodes/cases.csv')
    domains = pd.read_csv(f'{graph_dir}/nodes/legal_domains.csv')
    states = pd.read_csv(f'{graph_dir}/nodes/member_states.csv')
    actes = pd.read_csv(f'{graph_dir}/nodes/actes_uniformes.csv')
    articles = pd.read_csv(f'{graph_dir}/nodes/articles.csv')
    parties = pd.read_csv(f'{graph_dir}/nodes/parties.csv')
    
    # Create ID mappings
    case_id_map = {cid: i for i, cid in enumerate(cases['case_id'])}
    domain_id_map = {did: i for i, did in enumerate(domains['domain_id'])}
    state_id_map = {sid: i for i, sid in enumerate(states['state_id'])}
    acte_id_map = {aid: i for i, aid in enumerate(actes['acte_id'])}
    article_id_map = {int(a): i for i, a in enumerate(articles['article_number'])}
    party_id_map = {pid: i for i, pid in enumerate(parties['party_id'])}
    party_name_map = dict(zip(parties['name'], parties['party_id']))
    
    # Node counts
    data['case'].num_nodes = len(cases)
    data['domain'].num_nodes = len(domains)
    data['state'].num_nodes = len(states)
    data['acte'].num_nodes = len(actes)
    data['article'].num_nodes = len(articles)
    data['party'].num_nodes = len(parties)
    
    # Node features: year as a basic feature for cases
    years = cases['year'].fillna(0).values.astype(float)
    data['case'].x = torch.tensor(years, dtype=torch.float).unsqueeze(1)
    
    # Load edges
    def load_edges(file, src_col, tgt_col, src_map, tgt_map):
        df = pd.read_csv(f'{graph_dir}/edges/{file}')
        valid = df[src_col].map(src_map).notna() & df[tgt_col].map(tgt_map).notna()
        df = df[valid]
        src = torch.tensor(df[src_col].map(src_map).values.astype(int))
        tgt = torch.tensor(df[tgt_col].map(tgt_map).values.astype(int))
        return torch.stack([src, tgt], dim=0)
    
    # Case → cites → Case
    cite_df = pd.read_csv(f'{graph_dir}/edges/case_cites_case.csv')
    valid = cite_df['source_case_id'].isin(case_id_map) & cite_df['cited_case_id'].isin(case_id_map)
    cite_valid = cite_df[valid]
    if len(cite_valid) > 0:
        src = torch.tensor([case_id_map[x] for x in cite_valid['source_case_id']])
        tgt = torch.tensor([case_id_map[x] for x in cite_valid['cited_case_id']])
        data['case', 'cites', 'case'].edge_index = torch.stack([src, tgt])
    
    # Case → classified_as → Domain
    data['case', 'classified_as', 'domain'].edge_index = load_edges(
        'case_classified_as_domain.csv', 'case_id', 'domain_id', case_id_map, domain_id_map)
    
    # Case → originates_from → State
    data['case', 'originates_from', 'state'].edge_index = load_edges(
        'case_originates_from_state.csv', 'case_id', 'state_id', case_id_map, state_id_map)
    
    # Case → references → Acte
    data['case', 'references', 'acte'].edge_index = load_edges(
        'case_references_acte.csv', 'case_id', 'acte_id', case_id_map, acte_id_map)
    
    # Case → cites_article → Article
    art_df = pd.read_csv(f'{graph_dir}/edges/case_cites_article.csv')
    valid = art_df['case_id'].isin(case_id_map) & art_df['article_number'].isin(article_id_map)
    art_valid = art_df[valid]
    if len(art_valid) > 0:
        src = torch.tensor([case_id_map[x] for x in art_valid['case_id']])
        tgt = torch.tensor([article_id_map[int(x)] for x in art_valid['article_number']])
        data['case', 'cites_article', 'article'].edge_index = torch.stack([src, tgt])
    
    return data


# Usage:
data = load_ohada_graph('ohada_graph')
print(data)

import matplotlib
matplotlib.use('Agg')  # Force le rendu en mémoire sans interface graphique GUI
import matplotlib.pyplot as plt

# Supposons que 'data' est ton objet HeteroData déjà chargé
# On extrait un sous-échantillon des citations (case -> cites_article -> article)
edge_index = data['case', 'cites_article', 'article'].edge_index

# On prend les 30 premières relations pour ne pas surcharger l'image
sub_edge_index = edge_index[:, :30]

# Création d'un graphe NetworkX
G = nx.Graph()
for src, dst in sub_edge_index.t():
    G.add_edge(f"Arrêt {src.item()}", f"Art {dst.item()}")

# Affichage
plt.figure(figsize=(10, 8))
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=1500, font_size=8, font_weight='bold', edge_color='gray')
plt.title("Extrait du réseau de citations (Arrêts <-> Articles)")
plt.savefig('graphe_preview.png', dpi=300, bbox_inches='tight')
print("[✔] Image sauvegardée avec succès sous 'graphe_preview.png'")