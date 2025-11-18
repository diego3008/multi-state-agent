from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START, MessagesState, add_messages
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict, Annotated, Sequence
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
import operator
import os
import requests


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


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
def get_weather(city: str) -> str:
    """ This tool returns the current weather in a specific city 
        arguments:
            city: str
    """

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={WEATHER_API_KEY}"
    res = requests.get(url)

    if res.status_code == 200:
        temp_max = res.json()['main']['temp_max']
        name = res.json()['name']
        description = res.json()['weather'][0]['description']
        return f"In {name} is {temp_max} degrees with {description}"

    return f"there was a problem fetching the weather of {city}"


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

llm_with_tools = llm.bind_tools(all_tools)

SYSTEM_PROMPT = """You are a smart orchestrator that decides between multiple tool domains.

IMPORTANT - PARALELIZATION:
1. 
"""

class AgentState(TypedDict):

    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_domain: str
    iterations: int


def orchestrator_node(state: AgentState) -> AgentState:
    """ 
        This node receives user messages and decides which state and tools
        take for making what user asks.
    """

    messages = state["messages"]
    response = llm_with_tools.invoke(messages)



    return {
        "messages": [response],
        "next_action":  "determine_route"
    }


def determine_route(state: AgentState) -> str:
    """ 
    This function determines to which state go based on tool calls 
    """
    print(state["messages"])
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_names = [tc["name"] for tc in last_message.tool_calls]

        if any(name in ["get_sum", "get_division"] for name in tool_names):
            return "calculator"

        if any(name in ["get_weather", "get_time"] for name in tool_names):
            return "information"

    return "END"


def calculator_node(state: AgentState) -> AgentState:
    """
    Child node for managing mathematical operations
    """
    tool_node = ToolNode(tools_calculator)
    result = tool_node.invoke(state)

    return {
        "messages": result["messages"],
        "next_action": "orchestrator"
    }

def information_node(state: AgentState) -> AgentState:
    """
    Child node for managing mathematical operations
    """
    tool_node = ToolNode(tools_information)
    result = tool_node.invoke(state)

    return {
        "messages": result["messages"],
        "next_action": "orchestrator"
    }


def should_continue(state: AgentState) -> str:
    """
    Checks whether the conversation should continue or not
    """

    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    
    if isinstance(last_message, ToolMessage):
        return "orchestrator"
    
    return "END"



workflow = StateGraph(AgentState)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("calculator", calculator_node)
workflow.add_node("information", information_node)

workflow.add_edge(START, "orchestrator")
workflow.add_conditional_edges(
    "orchestrator",
    determine_route,
    {
        "calculator": "calculator",
        "information": "information",
        "END": END
    }

)

workflow.add_conditional_edges(
    "calculator",
    determine_route,
    {
        "orchestrator": "orchestrator",
        "continue": "calculator",
        "END": END
    }
    
)

workflow.add_conditional_edges(
    "information",
    determine_route,
    {
        "orchestrator": "orchestrator",
        "continue": "information",
        "END": END
    }
    
)

graph = workflow.compile()