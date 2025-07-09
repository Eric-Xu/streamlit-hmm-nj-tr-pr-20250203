import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from constants.css import (
    BLACK_HEX,
    BLUE_HEX,
    GREEN_HEX,
    GREEN_LIGHT_HEX,
    RED_HEX,
    YELLOW_HEX,
)

nodes, edges = [], []
nodes.extend(
    [
        Node(
            id="dec",
            label="  DEC '25  ",
            shape="circle",
            color=GREEN_HEX,
            labelColor=BLACK_HEX,
            borderWidth=0,
            physics=False,
            fixed={"x": True, "y": True},
            x=0,
            y=0,
        ),
        Node(
            id="nov",
            label="  NOV '25  ",
            shape="circle",
            color=GREEN_HEX,
            labelColor=BLACK_HEX,
            borderWidth=0,
            physics=False,
            fixed={"x": True, "y": True},
            x=0,
            y=100,
        ),
        Node(
            id="oct",
            label="  OCT '25  ",
            shape="circle",
            color=GREEN_HEX,
            labelColor=BLACK_HEX,
            borderWidth=0,
            physics=False,
            fixed={"x": True, "y": True},
            x=0,
            y=200,
        ),
    ]
)
nodes.extend(
    [
        Node(
            id="loan1",
            label=None,
            color=YELLOW_HEX,
            labelColor=BLACK_HEX,
            size=20,
            borderWidth=0,
            mass=2,
        ),
        Node(
            id="loan2",
            label=None,
            color=YELLOW_HEX,
            labelColor=BLACK_HEX,
            size=20,
            borderWidth=0,
            mass=2,
        ),
        Node(
            id="loan3",
            label=None,
            color=YELLOW_HEX,
            labelColor=BLACK_HEX,
            size=20,
            borderWidth=0,
            mass=2,
        ),
        Node(
            id="loan4",
            label=None,
            color=YELLOW_HEX,
            labelColor=BLACK_HEX,
            size=20,
            borderWidth=0,
            mass=2,
        ),
    ]
)
nodes.extend(
    [
        Node(
            id="lender1",
            label=None,
            color=RED_HEX,
            labelColor=BLACK_HEX,
            size=20,
            borderWidth=0,
            fixed={"x": True},
            x=400,
        ),
        Node(
            id="lender2",
            label=None,
            color=RED_HEX,
            labelColor=BLACK_HEX,
            size=20,
            borderWidth=0,
            fixed={"x": True},
            x=400,
        ),
    ]
)
edges.extend(
    [
        Edge(
            source="loan1",
            target="nov",
            color=GREEN_LIGHT_HEX,
            width=5,
        ),
        Edge(
            source="loan2",
            target="nov",
            color=GREEN_LIGHT_HEX,
            width=5,
        ),
        Edge(
            source="loan3",
            target="dec",
            color=GREEN_LIGHT_HEX,
            width=5,
        ),
        Edge(
            source="loan4",
            target="oct",
            color=GREEN_LIGHT_HEX,
            width=5,
        ),
    ]
)

edges.extend(
    [
        Edge(
            source="lender1",
            target="loan1",
            color=GREEN_LIGHT_HEX,
            width=5,
        ),
        Edge(
            source="lender1",
            target="loan2",
            color=GREEN_LIGHT_HEX,
            width=5,
        ),
        Edge(
            source="lender2",
            target="loan3",
            color=GREEN_LIGHT_HEX,
            width=5,
        ),
        Edge(
            source="lender2",
            target="loan4",
            color=GREEN_LIGHT_HEX,
            width=5,
        ),
    ]
)


config = Config(
    physics=True,
    directed=True,
    nodeHighlightBehavior=True,
    node={"labelProperty": "label"},
    link={"labelProperty": "label"},
)
agraph(nodes=nodes, edges=edges, config=config)
