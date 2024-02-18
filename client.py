from langserve import RemoteRunnable

server = RemoteRunnable("http://localhost:8080/langchain")

result = server.invoke({"question": "What is a new AI tool released recently?"})
print(result)