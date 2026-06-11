import os
import gradio as gr

from rag_agent.generator import generator_agent


def chat(message, history):
    return generator_agent(
        question=message,
        history=history
    )


demo = gr.ChatInterface(
    fn=chat,
    title="Veda Birthday Agent",
    description="Ask me anything about Veda's birthday 🎂"
)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 8080)),
        debug=True
    )