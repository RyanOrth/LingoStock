from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.agents import Tool
from langchain_community.tools.tavily_search import TavilySearchResults

from langchain.tools.retriever import create_retriever_tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
# from app.CachingRSSFeedLoader import CachingRSSFeedLoader
from langchain.pydantic_v1 import BaseModel


from datetime import datetime
import requests
import os
from pydantic import Field
from dotenv import load_dotenv

class Toolkit():
    def __init__(self) -> None:
        # self.polygon_key: str = Field(default_factory=lambda: os.getenv("POLYGON_API_KEY"))
        self.polygon_key = os.getenv("POLYGON_API_KEY")

        self.planning_tool = self.planning()
        # self.rss_retriever_tool = self.rss_retriever()
        self.tavily_search_tool = self.tavily_search()
        # self.pstocks_daily_open_close_tool = self.pstocks_daily_open_close()

    def get_tools(self):
        return [
            self.planning_tool,
            # self.rss_retriever_tool,
            self.tavily_search_tool,
            # self.pstocks_daily_open_close_tool,
        ]
    
    def planning(self):
        # Planning tool
        planning_prompt = PromptTemplate.from_template("You are a planner who is an expert at coming up with a todo list for a given objective. Come up with a todo list for this objective: {objective}")
        planning_chain = LLMChain(llm=ChatOpenAI(model="gpt-4", temperature=0), prompt=planning_prompt)

        planning_tool = Tool(
            name="Planning",
            func=planning_chain.run,
            description="useful for when you need to come up with todo lists. Input: an objective to create a todo list for. Output: a todo list for that objective. Please be very clear what the objective is!",
        )
        return planning_tool
    
    # def rss_retriever(self, urls, opml):
    #     # Retriever tool
    #     loader = CachingRSSFeedLoader(cache_dir="./app/.cache", urls=urls, opml=opml, show_progress_bar=True, browser_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    #     docs = loader.load()
    #     filtered_docs = filter_complex_metadata(docs)
    #     documents = RecursiveCharacterTextSplitter(
    #         chunk_size=1000, chunk_overlap=200
    #     ).split_documents(filtered_docs)
        
    #     vector = Chroma.from_documents(documents, OpenAIEmbeddings())
    #     retriever = vector.as_retriever()

    #     retriever_tool = create_retriever_tool(
    #         retriever,
    #         "rss_retriever",
    #         "Scour different rss feeds for information",
    #     )
    #     return retriever_tool

    def tavily_search(self):
        return TavilySearchResults(max_results=1)
    
    class PstocksDailyOpenCloseInput(BaseModel):
        stocksTicker: str = Field(description="Stock ticker for a company")
        dateTextYYYYMMDD: str = Field(description="A date in the string format 'YYYY-MM-DD' that is the requested open/closing stock price date")


    def pstocks_daily_open_close(self):
        polygon_stocks_tool = Tool(
            name="Stocks Daily Open Close",
            func=self.call_pstocks_daily_open_close,
            args_schema=self.PstocksDailyOpenCloseInput,
            return_direct=True,
            description="Useful for when you need to get the daily opening and closing stock prices. Requires both a stock ticker and date in string format"
        )
        return polygon_stocks_tool


    def call_pstocks_daily_open_close(self, stocksTicker: str, dateTextYYYYMMDD: str) -> str:
        try:
            # Check if the date is in the correct format
            valid_date = datetime.strptime(dateTextYYYYMMDD, '%Y-%m-%d')
            valid_date = dateTextYYYYMMDD
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DD")

        # Construct the full URL with parameters
        url = f"https://api.polygon.io/v1/open-close/{stocksTicker}/{valid_date}"

        params = {
            "adjusted": "true",
            "apiKey": self.polygon_key
        }

        # Make the GET request
        r = requests.get(url, params=params)

        # Check for errors
        r.raise_for_status()

        # Return the JSON response
        return str(r.json())