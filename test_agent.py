from rag_agent.generator import generator_agent

question = "What is Veda's birthday date?"

response = generator_agent(question)

print("\nFinal Response:")
print(response)