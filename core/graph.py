from langgraph.graph import StateGraph, END
from core.nodes import SessionState, assemble_context, generate_response

def build_graph():
    graph = StateGraph(SessionState)

    graph.add_node("assemble_context", assemble_context)
    graph.add_node("generate_response", generate_response)

    graph.set_entry_point("assemble_context")
    graph.add_edge("assemble_context", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()
