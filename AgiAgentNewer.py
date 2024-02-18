from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_experimental.autonomous_agents import BabyAGI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.agents import AgentExecutor, Tool, ZeroShotAgent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langchain_community.agent_toolkits.polygon.toolkit import PolygonToolkit
from langchain_community.utilities.polygon import PolygonAPIWrapper
from typing import Optional
import os

load_dotenv()

langchain_key = os.getenv("LANGCHAIN_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")
polygon_key = os.getenv("POLYGON_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

embeddings = OpenAIEmbeddings()
vectorstore = Chroma("langchain_agi_store", embeddings)

planning_prompt = PromptTemplate.from_template("You are a planner who is an expert at coming up with a todo list for a given objective. Come up with a todo list for this objective: {objective}")
planning_chain = LLMChain(llm=ChatOpenAI(model="gpt-4", temperature=0), prompt=planning_prompt)

tools = [
    TavilySearchResults(max_results=1),
    YahooFinanceNewsTool(),
    *PolygonToolkit.from_polygon_api_wrapper(PolygonAPIWrapper(polygon_api_key=polygon_key)).get_tools(),
    Tool(
        name="Planning",
        func=planning_chain.run,
        description="useful for when you need to come up with todo lists. Input: an objective to create a todo list for. Output: a todo list for that objective. Please be very clear what the objective is!",
    )
]

prefix = """You are an AI who performs one task based on the following objective: {objective}. Take into account these previously completed tasks: {context}."""
suffix = """Question: {task}
{agent_scratchpad}"""
prompt = ZeroShotAgent.create_prompt(
    tools,
    prefix=prefix,
    suffix=suffix,
    input_variables=["objective", "task", "context", "agent_scratchpad"],
)

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
llm_chain = LLMChain(llm=llm, prompt=prompt)
tool_names = [tool.name for tool in tools]
agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# OBJECTIVE = "Write a weather report for West Fargo today"
OBJECTIVE = "Give me a stock report for Microsoft"

# Logging of LLMChains
verbose = False
# If None, will keep on going forever
max_iterations: Optional[int] = 3
baby_agi = BabyAGI.from_llm(
    llm=llm,
    vectorstore=vectorstore,
    task_execution_chain=agent_executor,
    verbose=verbose,
    max_iterations=max_iterations,
)

baby_agi.invoke({"objective": OBJECTIVE})