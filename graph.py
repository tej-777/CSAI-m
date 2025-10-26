from langgraph import Workflow, Node
from agents.router_agent import route_query
from agents.summarizer_agent import summarize_output
from agents.critic_agent import provide_feedback

class CustomerSupportWorkflow(Workflow):
    def __init__(self):
        super().__init__(name="CustomerSupportWorkflow")
        self.add_node(Node("router", route_query))
        self.add_node(Node("summarizer", summarize_output))
        self.add_node(Node("critic", provide_feedback))
        self.add_edge("router", "summarizer")
        self.add_edge("summarizer", "critic")
        self.add_edge("critic", "end")

    def run(self, query):
        result = self.execute({"router": query})
        return result

workflow = CustomerSupportWorkflow()
