import pickle
import networkx as nx
import matplotlib.pyplot as plt

# Đọc file pickle
with open("book_graph.pickle", "rb") as f:
    graph = pickle.load(f)

# Vẽ graph
pos = nx.spring_layout(graph)  # Bố trí node
nx.draw(
    graph, pos, with_labels=True, node_color="lightblue", node_size=500, font_size=8
)
plt.title("Graph Quan Hệ Sách")
plt.show()
