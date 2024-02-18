from langserve import RemoteRunnable

server = RemoteRunnable("https://ai.kvan.dev/langchain")

result = server.invoke({"question": "What is a new AI tool released recently?"})
print(result)