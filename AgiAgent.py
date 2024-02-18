from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_experimental.autonomous_agents import BabyAGI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.agents import AgentExecutor, Tool, ZeroShotAgent, create_react_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import Optional

from pprint import pprint

load_dotenv()

embeddings = OpenAIEmbeddings()
vectorstore = Chroma("langchain_agi_store", embeddings)

planning_prompt = PromptTemplate.from_template("You are a planner who is an expert at coming up with a todo list for a given objective. Come up with a todo list for this objective: {objective}")
planning_chain = LLMChain(llm=ChatOpenAI(model="gpt-4", temperature=0), prompt=planning_prompt)

tools = [
    TavilySearchResults(max_results=1),
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
# # llm_chain = LLMChain(llm=llm, prompt=prompt)
# tool_names = [tool.name for tool in tools]
# agent = create_react_agent(llm=llm, tools=tool_names, prompt=prompt)
llm_chain = LLMChain(llm=llm, prompt=prompt)
tool_names = [tool.name for tool in tools]
agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

OBJECTIVE = "Write a weather report for Lincoln today"

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

result = baby_agi.invoke({"objective": OBJECTIVE})

# print(baby_agi.results)
vector_store = baby_agi.vectorstore
vector_store
print(baby_agi.task_list)
print('\n\n\n')
print(baby_agi.task_creation_chain)
print('\n\n\n')
print(baby_agi.tags)
print('\n\n\n')
pprint(baby_agi.to_json())
# pprint(vars(baby_agi.execution_chain))
# print('\n\n\n\n')
# pprint(vars(baby_agi))
# print(result)
# for result in baby_agi.({"objective": OBJECTIVE}):
#     print(result)

# print(baby_agi.task_list)