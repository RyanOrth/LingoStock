from typing import Optional
from langchain_core.runnables import Runnable, RunnableConfig
import os
from dotenv import load_dotenv

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools.retriever import create_retriever_tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from app.CachingRSSFeedLoader import CachingRSSFeedLoader

class LangChainRunnable(Runnable):
    def __init__(self):
        load_dotenv()
        self.langchain_key = os.getenv("LANGCHAIN_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.setup()

    def setup(self):
        search = TavilySearchResults()
        # search.invoke("what is the weather in Lincoln")

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

        # print(retriever.get_relevant_documents("api reference")[0])
        retriever_tool = create_retriever_tool(
            retriever,
            "langchain_search",
            "Search for information about LangChain. For any questions about LangChain, you must use this tool!"
        )

        tools = [search, retriever_tool]

        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        prompt = hub.pull("hwchase17/openai-functions-agent")

        agent = create_openai_functions_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        # result = agent_executor.invoke({"input": "How do I create an agent with LangChain"} "chat_history": [])
        # print(result)

        message_history = ChatMessageHistory()

        self.agent_with_chat_history = RunnableWithMessageHistory(
            agent_executor,
            # This is needed because in most real world scenarios, a session id is needed
            # It isn't really used here because we are using a simple in memory ChatMessageHistory
            lambda session_id: message_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    def invoke(self, input_data: dict, config: Optional[RunnableConfig] = None) -> str:
        # Your main logic here, using input_data as needed
        # For example, you might want to process a question and return an answer
        # This is a simplified example; adjust according to your actual logic
        question = input_data.get("question", "")
        print(input_data)
        print(config)
        answer = self.process_question(question, config=config)
        return answer

    def process_question(self, question: str, config: Optional[RunnableConfig] = None) -> str:
        # Implement your processing logic here
        # This should return a string that is the answer to the given question
        config["configurable"] = {"session_id": "<foo>"}
        output = self.agent_with_chat_history.invoke(
            {"input": question},
            config=config
        )
        return output["output"]
