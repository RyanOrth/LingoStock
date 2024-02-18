from typing import Any, List, Optional
from langchain_core.runnables import Runnable, RunnableConfig
import os

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents import AgentExecutor, create_openai_functions_agent, create_openai_tools_agent
from langchain.tools.retriever import create_retriever_tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import Field

from app.CachingRSSFeedLoader import CachingRSSFeedLoader
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.callbacks import Callbacks, CallbackManagerForLLMRun

class LangChainRunnable(BaseChatModel):
    langchain_key: str = Field(default_factory=lambda: os.getenv("LANGCHAIN_API_KEY"))
    openai_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    tavily_key: str = Field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))

    agent_executor: Optional[AgentExecutor] = None
    agent_with_chat_history: Optional[RunnableWithMessageHistory] = None
    message_history: Optional[ChatMessageHistory] = None

    def __init__(self, **data):
        super().__init__(**data)  # Pass the data to the parent class
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

        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, streaming=True)
        prompt = hub.pull("hwchase17/openai-functions-agent")

        agent = create_openai_functions_agent(llm, tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        # result = agent_executor.invoke({"input": "How do I create an agent with LangChain"} "chat_history": [])
        # print(result)

        self.message_history = ChatMessageHistory()

        self.agent_with_chat_history = RunnableWithMessageHistory(
            self.agent_executor,
            # This is needed because in most real world scenarios, a session id is needed
            # It isn't really used here because we are using a simple in memory ChatMessageHistory
            lambda session_id: self.message_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    @property
    def input_schema(self, config: Optional[RunnableConfig]) -> dict:
        return {
            "question": {
                "type": "string",
                "description": "The question to be answered"
            }
        }
    
    @property
    def output_schema(self) -> dict:
        return {
            "answer": {
                "type": "string",
                "description": "The answer to the given question"
            }
        }

    def process_question(self, messages: List[BaseMessage], config: Optional[RunnableConfig] = {"configurable":{"session_id":"<foo>"}}) -> str:
        self.message_history.clear()
        self.message_history.add_messages(messages[:-1])
        output = self.agent_with_chat_history.invoke(
            {"input": messages[-1].content},
            config=config
        )
        return output["output"]

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        response_content = self.process_question(messages)
        response_message = AIMessage(content=response_content)
        return ChatResult(generations=[ChatGeneration(message=response_message)])

    def _llm_type(self) -> str:
        return "openai"

