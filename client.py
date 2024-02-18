from langserve import RemoteRunnable

server = RemoteRunnable("http://localhost:8000/langchain")

result = server.invoke("What is a new AI tool released recently?")
print(result)