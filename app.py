from streamlit_agraph import Config, Edge, Node, agraph

nodes = [
    Node(
        id="Spiderman",
        label="Spiderman",
        color="#FF0000",
        labelColor="#FFFFFF",
        size=10,
        shape="diamond",
    ),
    Node(
        id="Captain_Marvel",
        label="Captain Marvel",
        color="#0000FF",
        labelColor="#FFFFFF",
        size=25,
        shape="diamond",
    ),
]

edges = [Edge(source="Captain_Marvel", label="friend_of", target="Spiderman")]

config = Config(
    width=500,
    height=400,
    directed=True,
    nodeHighlightBehavior=True,
    node={"labelProperty": "label"},
    link={"labelProperty": "label"},
)

agraph(nodes=nodes, edges=edges, config=config)
