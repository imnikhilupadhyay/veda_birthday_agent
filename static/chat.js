window.addEventListener("DOMContentLoaded", () => {
    appendMessage("Hi! How can I help you? 🎂", "bot");
});

async function sendMessage() {
    const input = document.getElementById("message-input");
    const chatBox = document.getElementById("chat-box");

    const message = input.value.trim();
    if (!message) return;

    appendMessage(message, "user");
    input.value = "";

    let thinkingBox = appendThinkingBox("Thinking...");
    let botMessage = null;
    let fullText = "";

    const response = await fetch("/chat-stream", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let buffer = "";

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
            if (!line.trim()) continue;

            const event = JSON.parse(line);

            if (event.type === "thinking_start") {
                if (!thinkingBox) {
                    thinkingBox = appendThinkingBox("Thinking...");
                }
            }

            if (event.type === "thinking_update") {
                if (!thinkingBox) {
                    thinkingBox = appendThinkingBox(event.content);
                } else {
                    thinkingBox.innerText = event.content;
                }
            }

            if (event.type === "answer_start") {
                // Do nothing here.
                // Keep the soft thinking box visible until the first token arrives.
            }

            if (event.type === "token") {
                if (thinkingBox) {
                    thinkingBox.remove();
                    thinkingBox = null;
                }

                if (!botMessage) {
                    botMessage = appendMessage("", "bot");
                }

                fullText += event.content;
                botMessage.innerText = fullText;
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        }
    }

    if (thinkingBox) {
        thinkingBox.remove();
    }
}

function appendMessage(text, role, id = null) {
    const chatBox = document.getElementById("chat-box");

    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.innerText = text;

    if (id) {
        div.id = id;
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;

    return div;
}

function appendThinkingBox(text) {
    const chatBox = document.getElementById("chat-box");

    const div = document.createElement("div");
    div.className = "thinking-shadow";
    div.innerText = text;

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;

    return div;
}

document.getElementById("message-input").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});