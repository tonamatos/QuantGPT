# /src/quantgpt/knowledge_graph.py

import sqlite3
from collections import defaultdict
from pprint import pprint

class KnowledgeGraph:
    def __init__(self):
        self.nodes = {}  # {id: {"label": str, "props": dict}}
        self.relationships = defaultdict(list)  # {src_id: [(rel_type, dst_id)]}
        self.next_id = 1

    def add_node(self, label, props):
        """Add a node with a label (like 'Algorithm') and properties."""
        node_id = self.next_id
        self.next_id += 1
        self.nodes[node_id] = {"label": label, "props": props}
        return node_id

    def add_relationship(self, src_id, rel_type, dst_id):
        """Add a relationship of type rel_type from src -> dst."""
        self.relationships[src_id].append((rel_type, dst_id))

    def find_node_by_prop(self, key, value):
        """Return all node_ids that match a property."""
        return [
            node_id for node_id, data in self.nodes.items()
            if data["props"].get(key) == value
        ]

    # === Query helpers ===
    def get_protocols_using_algorithm(self, algo_name):
        algo_ids = self.find_node_by_prop("algo_name", algo_name)
        protocols = []
        for algo_id in algo_ids:
            for rel, dst in self.relationships[algo_id]:
                if rel == "USED_IN" and self.nodes[dst]["label"] == "Protocol":
                    protocols.append(self.nodes[dst]["props"])
        return protocols

    def get_vulnerabilities(self, entity_name):
        entity_ids = self.find_node_by_prop("entity_name", entity_name)
        vulns = []
        for eid in entity_ids:
            for rel, dst in self.relationships[eid]:
                if rel == "HAS_ASSESSMENT":
                    ra = self.nodes[dst]
                    for rel2, dst2 in self.relationships[dst]:
                        if rel2 == "HAS_VULNERABILITY":
                            vulns.append(self.nodes[dst2]["props"])
        return vulns

    def get_risk_assessments(self, entity_name):
        entity_ids = self.find_node_by_prop("entity_name", entity_name)
        assessments = []
        for eid in entity_ids:
            for rel, dst in self.relationships[eid]:
                if rel == "HAS_ASSESSMENT":
                    assessments.append(self.nodes[dst]["props"])
        return assessments


def build_graph_from_sqlite(db_path):
    """Read pq_risk.db and build the in-memory graph."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    G = KnowledgeGraph()

    # Entities
    cur.execute("SELECT entity_id, entity_type, entity_name FROM entities")
    entity_map = {}
    for eid, etype, ename in cur.fetchall():
        node_id = G.add_node("Entity", {"entity_id": eid, "entity_type": etype, "entity_name": ename})
        entity_map[eid] = node_id

    # Algorithms
    cur.execute("SELECT algorithm_id, entity_id, algo_name, algo_family, crypto_type FROM algorithms")
    for aid, eid, name, fam, ctype in cur.fetchall():
        algo_id = G.add_node("Algorithm", {"algorithm_id": aid, "algo_name": name, "algo_family": fam, "crypto_type": ctype})
        G.add_relationship(algo_id, "IS_ENTITY", entity_map[eid])

    # Protocols
    cur.execute("SELECT protocol_id, entity_id, protocol_name, cipher_suites FROM protocols")
    for pid, eid, name, suites in cur.fetchall():
        proto_id = G.add_node("Protocol", {"protocol_id": pid, "protocol_name": name, "cipher_suites": suites})
        G.add_relationship(proto_id, "IS_ENTITY", entity_map[eid])

    # Certificates
    cur.execute("SELECT cert_id, entity_id, cert_name, recommended_crypto_suite FROM certificates")
    for cid, eid, name, suite in cur.fetchall():
        cert_id = G.add_node("Certificate", {"cert_id": cid, "cert_name": name, "recommended_crypto_suite": suite})
        G.add_relationship(cert_id, "IS_ENTITY", entity_map[eid])

    # Vulnerabilities
    cur.execute("SELECT vuln_id, vuln_type FROM vulnerabilities")
    vuln_map = {}
    for vid, vtype in cur.fetchall():
        vuln_id = G.add_node("Vulnerability", {"vuln_id": vid, "vuln_type": vtype})
        vuln_map[vid] = vuln_id

    # LIR
    cur.execute("SELECT lir_id, likelihood, impact, overall_risk FROM lir")
    lir_map = {}
    for lid, l, i, o in cur.fetchall():
        lir_id = G.add_node("LIR", {"lir_id": lid, "likelihood": l, "impact": i, "overall_risk": o})
        lir_map[lid] = lir_id

    # Risk assessments
    cur.execute("SELECT assessment_id, entity_id, vuln_id, lir_id, quant_stride FROM risk_assessments")
    for rid, eid, vid, lid, stride in cur.fetchall():
        ra_id = G.add_node("RiskAssessment", {"assessment_id": rid, "quant_stride": stride})
        G.add_relationship(entity_map[eid], "HAS_ASSESSMENT", ra_id)
        if vid in vuln_map:
            G.add_relationship(ra_id, "HAS_VULNERABILITY", vuln_map[vid])
        if lid in lir_map:
            G.add_relationship(ra_id, "HAS_RISK", lir_map[lid])

    conn.close()
    return G

def summarize_graph(G: KnowledgeGraph):
    """Prints a summary of the graph: node counts by type and relationship counts by type."""
    from collections import Counter

    node_counter = Counter([data["label"] for data in G.nodes.values()])
    rel_counter = Counter([rel for src in G.relationships for rel, _ in G.relationships[src]])

    print("\n=== Graph Summary ===")
    print("Nodes by label:")
    for label, count in node_counter.items():
        print(f"  {label}: {count}")

    print("\nRelationships by type:")
    for rel, count in rel_counter.items():
        print(f"  {rel}: {count}")


if __name__ == "__main__":
    db_path = "src/databases/pq_risk.db"
    G = build_graph_from_sqlite(db_path)

    # Existing demo
    entity_nodes = [n for n, d in G.nodes.items() if d["label"] == "Entity"]
    print("\n=== First 4 Entities ===")
    for node_id in entity_nodes[:4]:
        pprint(G.nodes[node_id]["props"])

    print("\n=== Sample Queries ===")
    for node_id in entity_nodes[:4]:
        name = G.nodes[node_id]["props"]["entity_name"]
        print(f"\nEntity: {name}")

        print("Vulnerabilities:")
        pprint(G.get_vulnerabilities(name))

        print("Risk Assessments:")
        pprint(G.get_risk_assessments(name))

    # New summary
    print("\n=== Full Graph Summary ===")
    summarize_graph(G)