from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START, MessagesState, add_messages
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict, Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
import os


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

llm = ChatOpenAI(model="gpt-4o", temperature=0)


# Tools

@tool
def get_sum(a: int, b: int) -> int:
    """ Returns a sum between two numbers 'a' and 'b' 
        arguments:
            a: int
            b: int
    """

    return a + b


@tool
def get_division(a: int, b: int) -> int:
    """ Returns a division between two numbers 'a' and 'b' 
        arguments:
            a: int
            b: int
    """
    return a // b

@tool
def get_weather(city: str):
    """ This tool returns the current weather in a specific city 
        arguments:
            city: str
    """

    pass

@tool
def get_time(city: str):
    """ This tool return the time in a specific city 
        arguments:
            city: str
    """

    pass

tools_calculator = [get_sum, get_division]
tools_information = [get_weather, get_time]
all_tools = tools_calculator + tools_information


class AgentState(TypedDict):

    messages: Annotated[list[BaseMessage], add_messages]

    next_action: str


def orchestrator_node(state: AgentState) -> AgentState:
    """ 
        This node receives user messages and decides which state and tools
        take for making what user asks.
    """

    messages = state["messages"]

    return {
        "messages": messages,
        "next_action":  "determine_route"
    }


