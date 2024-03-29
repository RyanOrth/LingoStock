import os
from dotenv import load_dotenv

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools.retriever import create_retriever_tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.document_loaders import RSSFeedLoader
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from server.app.CachingRSSFeedLoader import CachingRSSFeedLoader

def main():
    load_dotenv()

    langchain_key = os.getenv("LANGCHAIN_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    search = TavilySearchResults()
    # search.invoke("what is the weather in Lincoln")

    with open("rss_urls.txt") as f:
        urls = f.readlines()
    
    loader = CachingRSSFeedLoader(cache_dir="./.cache", urls=urls, show_progress_bar=True, browser_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
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

    agent_with_chat_history = RunnableWithMessageHistory(
        agent_executor,
        lambda session_id: message_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    output = agent_with_chat_history.invoke(
        {"input": "What are some interesting AI companies?"},
        config={"configurable": {"session_id": "<foo>"}}
    )


if __name__ == '__main__':
    main()