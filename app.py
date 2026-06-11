import os
import gradio as gr

from rag_agent.generator import generator_agent


def chat(message, history):
    print(f"User message: {message}", flush=True)
    print(f"History: {history}", flush=True)

    response = generator_agent(
        question=message,
        history=history
    )

    print(f"Assistant response: {response}", flush=True)

    return {
        "role": "assistant",
        "content": response
    }


demo = gr.ChatInterface(
    fn=chat,
    title="Veda Birthday Agent",
    description="Ask me anything about Veda's birthday 🎂"
)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 8080))
    )