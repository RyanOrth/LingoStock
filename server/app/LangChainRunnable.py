from typing import Optional
from langchain_core.runnables import Runnable, RunnableConfig
import os
from dotenv import load_dotenv

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain.chains import LLMChain
from langchain_core.messages import AIMessage, HumanMessage
from langchain.prompts import PromptTemplate
from langchain.agents import AgentExecutor, Tool, create_openai_functions_agent, ZeroShotAgent
from langchain.tools.retriever import create_retriever_tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_experimental.autonomous_agents import BabyAGI

from app.CachingRSSFeedLoader import CachingRSSFeedLoader

class LangChainRunnable(Runnable):
    def __init__(self):
        load_dotenv()
        self.langchain_key = os.getenv("LANGCHAIN_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.setup()

    def setup(self):
        with open("./app/rss_urls.txt") as f:
            urls = f.readlines()
        
        loader = CachingRSSFeedLoader(cache_dir="./app/.cache", urls=urls, show_progress_bar=True, browser_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        docs = loader.load()
        filtered_docs = filter_complex_metadata(docs)
        documents = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        ).split_documents(filtered_docs)
        
        vector = Chroma.from_documents(documents, OpenAIEmbeddings())
        retriever = vector.as_retriever()

        finance_rss_feeds_retriever_tool = create_retriever_tool(
            retriever,
            "finance_rss_feeds",
            "Search for information about stocks from finance news articles. For any questions about stock news, you must use this tool!"
        )

        planning_prompt = PromptTemplate.from_template("You are a planner who is an expert at coming up with a todo list for a given objective. Come up with a todo list for this objective: {objective}")
        planning_chain = LLMChain(llm=ChatOpenAI(model="gpt-4", temperature=0), prompt=planning_prompt)

        tools = [
            finance_rss_feeds_retriever_tool,
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
        llm_chain = LLMChain(llm=llm, prompt=prompt)
        tool_names = [tool.name for tool in tools]
        agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # message_history = ChatMessageHistory()

        # agent_with_chat_history = RunnableWithMessageHistory(
        #     agent_executor,
        #     # This is needed because in most real world scenarios, a session id is needed
        #     # It isn't really used here because we are using a simple in memory ChatMessageHistory
        #     lambda session_id: message_history,
        #     input_messages_key="input",
        #     history_messages_key="chat_history",
        # )

        vectorstore = Chroma("agi_local_store", OpenAIEmbeddings())

        # Logging of LLMChains
        verbose = False
        # If None, will keep on going forever
        max_iterations: Optional[int] = 3
        self.babyAGI_agent = BabyAGI.from_llm(
            llm=llm,
            vectorstore=vectorstore,
            task_execution_chain=agent_executor,
            # task_execution_chain=agent_with_chat_history,
            verbose=verbose,
            max_iterations=max_iterations,
        )

    def invoke(self, input_data: dict, config: Optional[RunnableConfig] = None) -> str:
        # Your main logic here, using input_data as needed
        # For example, you might want to process a question and return an answer
        # This is a simplified example; adjust according to your actual logic
        print(input_data)
        print(config)
        objective = input_data.get("objective", "")
        answer = self.process_question(objective, config=config)
        return answer

    def process_question(self, objective: str, config: Optional[RunnableConfig] = None) -> str:
        # Implement your processing logic here
        # This should return a string that is the answer to the given question
        config["configurable"] = {"session_id": "<foo>"}
        # output = self.agent_with_chat_history.invoke(
        #     {"input": question},
        #     config=config
        # )
        output = self.babyAGI_agent.invoke(
            {"objective": objective}
        )
        print(output)
        return output["output"]
