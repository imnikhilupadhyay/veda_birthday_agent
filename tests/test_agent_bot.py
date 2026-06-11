from rag_agent.generator import generator_agent

history = []

while True:
    question = input("\nYou: ")

    if question.lower() in ["exit", "quit"]:
        break

    response = generator_agent(question, history)

    print(f"\nVeda: {response}")

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": response})