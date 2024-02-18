# LingoStock

CornHacks 2024 - Ryan Orth, Garrett Parker

## Purpose

This is a project that uses the LangChain library to make a Large Language Model agent to do tasks.

We have connected our LLM agent to rss feeds to get the latest news in the financial world. The LLM agent can read articles and store them for future queries, which allows it to provide informed recommendations about stocks.

There are two kinds of LLM agents our project supports. One is a query-based agent, similar to ChatGPT, where you ask the agent a question and it uses internet searches combined with specific rss feeds to answer the query.

The second kind of LLM agent in our project uses BabyAGI (Artificial General Intelligence). The agent receives an objective, creates a plan on how to achieve that objective (via to-do list), and works to accomplish/update that to-do list to deliver on the objective. This allows our agent to operate with more autonomy and come up with creative solutions to our objectives.

## Installation and Setup

After cloning the repository, open it in a dev-container.

The dev-container should automatically install dependencies, but the following command will manually install them:

```bash
pip install -r requirements.txt
```

### .env File

Create a file called `.env` in the project root directory and in the `server` directory. Add the corresponding API keys:

```sh
LANGCHAIN_API_KEY="YOUR_KEY_HERE"
OPENAI_API_KEY="YOUR_KEY_HERE"
POLYGON_API_KEY="YOUR_KEY_HERE"
TAVILY_API_KEY="YOUR_KEY_HERE"
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_PROJECT="LingoStock"
```

## Running the Project

Run the following command in the `server` directory to build the project's API.

```
docker compose up
```

It can be accessed from the `local:8080` port. View the two API playgrounds using `local:8080/agi/playground` or `local:8080/query/playground`.

## AGI Script Testing

To test the AGI Agent without fully building the API, manually adjust the prompt in `AgiAgent.py` and run the following command:

```
python AgiAgent.py
```

This will allow you to see the agent's thought process when executing tasks.

# API Documentation

With FastAPI, our api endpoints are documented and allow users to test out the system.

# Examples

To understand the LLM Agent's thought process when completing an objective, see the following [Example AGI Agent Query](ExampleQueryAGI.md).