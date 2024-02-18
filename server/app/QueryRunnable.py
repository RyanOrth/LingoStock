from typing import Any, List, Optional, Tuple
from langchain_core.runnables import Runnable, RunnableConfig
import os

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
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
from langchain_core.chat_history import BaseChatMessageHistory
from app.CachingRSSFeedLoader import CachingRSSFeedLoader
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

class QueryRunnable(BaseChatModel):
    langchain_key: str = Field(default_factory=lambda: os.getenv("LANGCHAIN_API_KEY"))
    openai_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    tavily_key: str = Field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))

    agent_executor: Optional[AgentExecutor] = None
    agent_with_chat_history: Optional[RunnableWithMessageHistory] = None
    message_history: Optional[ChatMessageHistory] = None

    def __init__(self, **data):
        super().__init__(**data)
        self.setup()

    def setup(self):
        with open("./app/rss_urls.txt") as f:
            urls = f.readlines()
        
        self.agent_with_chat_history= self.create_agent(urls)


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
    
    def create_agent(self, urls: List[str], opml: str = None) -> RunnableWithMessageHistory:
        search = TavilySearchResults()

        loader = CachingRSSFeedLoader(cache_dir="./app/.cache", urls=urls, opml=opml, show_progress_bar=True, browser_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        print(loader._get_urls())
        docs = loader.load()
        filtered_docs = filter_complex_metadata(docs)
        documents = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        ).split_documents(filtered_docs)
        vector = Chroma.from_documents(documents, OpenAIEmbeddings())
        retriever = vector.as_retriever()

        retriever_tool = create_retriever_tool(
            retriever,
            "rss_retriever",
            "Look up information in provided rss feeds. You can only use the available feeds.\nAvailable rss feeds: " + ", ".join(urls) if not opml else opml,
        )

        tools = [ retriever_tool]

        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, streaming=True)
        prompt = hub.pull("hwchase17/openai-functions-agent")

        agent = create_openai_functions_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

        agent_with_chat_history = RunnableWithMessageHistory(
            agent_executor,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        return agent_with_chat_history
    
    def new_rss_system(self, messages: List[BaseMessage], is_opml: bool = False) -> RunnableWithMessageHistory:
        if is_opml:
            rss_feeds = messages[0].content
            agent = self.create_agent(None, opml=messages[0].content)
        else:
            rss_feeds = messages[0].content.splitlines()[1:]
            agent = self.create_agent(rss_feeds)
        return agent

    def process_question(self, messages: List[BaseMessage], config: Optional[RunnableConfig] = {"configurable":{"session_id":"<foo>"}}) -> str:
        len_req = 1
        if isinstance(messages[0], SystemMessage):
            if "rss" in messages[0].content.splitlines()[0].lower():
                agent = self.new_rss_system(messages)
            elif "<?xml version='1.0' encoding='UTF-8' ?>" in messages[0].content.splitlines()[0] \
                    and "<opml version=" in messages[0].content.splitlines()[1]:
                agent = self.new_rss_system(messages, is_opml=True)
            len_req = 2
        else:
            agent = self.agent_with_chat_history

        if len(messages) > len_req:
            history = get_session_history(config["configurable"]["session_id"])
            history.add_messages(messages[:-1] if len_req == 1 else messages[1:-1])
            print("History: ", history.messages)
        output = agent.invoke(
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
        response_content = self.process_question(messages, config={"configurable":{"session_id":run_manager.run_id}})
        response_message = AIMessage(content=response_content)
        return ChatResult(generations=[ChatGeneration(message=response_message)])

    def _llm_type(self) -> str:
        return "openai"

