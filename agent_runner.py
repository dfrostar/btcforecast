from smolagents import CodeAgent, OllamaModel

# Use the local 'mistral:latest' model via Ollama
model = OllamaModel(model_id="mistral:latest")

# Create an agent with default tools (web search, etc.)
agent = CodeAgent(
    tools=[],  # You can add custom tools here
    model=model,
    add_base_tools=True  # Adds web search and other default tools
)

# Run a sample task
task = "What is the current price of Bitcoin?"
result = agent.run(task)
print("[AGENT RESULT]", result) 