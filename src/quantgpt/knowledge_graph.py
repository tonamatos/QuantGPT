import networkx as nx
import csv

def add_nodes_from_csv(graph, csv_path):
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Use a unique identifier for each node, e.g., row['id']
            # All other columns become node attributes
            node_id = row.get('id', None)
            if node_id:
                graph.add_node(node_id, **row)
            else:
                # If no 'id' column, use row index or another unique value
                graph.add_node(str(row), **row)

if __name__ == "__main__":
    G = nx.Graph()
    add_nodes_from_csv(G, '.csv')