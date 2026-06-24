window.addEventListener("DOMContentLoaded", () => {
    const greeting = document.body.dataset.greeting || "Hi! How can I help you? 🎂";
    appendMessage(greeting, "bot");
});

function appendErrorMessage(text) {
    const chatBox = document.getElementById("chat-box");

    const div = document.createElement("div");
    div.className = "message error-message";
    div.innerText = text;

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;

    return div;
}

async function sendMessage() {
    const input = document.getElementById("message-input");
    const chatBox = document.getElementById("chat-box");

    const message = input.value.trim();
    if (!message) return;
    removeSuggestionBoxes();

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

            else if (event.type === "thinking_update") {
                if (!thinkingBox) {
                    thinkingBox = appendThinkingBox(event.content);
                } else {
                    thinkingBox.innerText = event.content;
                }
            }

            else if (event.type === "answer_start") {
                // Do nothing here.
                // Keep thinking box visible until first token arrives.
            }

            else if (event.type === "token") {
                if (thinkingBox) {
                    thinkingBox.remove();
                    thinkingBox = null;
                }

                if (!botMessage) {
                    botMessage = appendMessage("", "bot");
                }

                fullText += event.content;
                botMessage.innerHTML = linkify(fullText);
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            else if (event.type === "suggestions") {
                appendSuggestionButtons(event.content, event.options);
            }

            else if (event.type === "error") {
                if (thinkingBox) {
                    thinkingBox.remove();
                    thinkingBox = null;
                }

                appendErrorMessage("ⓘ " + event.content);
            }
        }
    }

    if (!botMessage && thinkingBox) {
        thinkingBox.remove();
        thinkingBox = null;

        appendMessage(
            "I don't know based on the available birthday information.",
            "bot"
        );
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

function appendSuggestionButtons(title, options) {
    const chatBox = document.getElementById("chat-box");

    const wrapper = document.createElement("div");
    wrapper.className = "suggestion-box";

    const label = document.createElement("div");
    label.className = "suggestion-title";
    label.innerText = title;

    wrapper.appendChild(label);

    options.forEach(option => {
        const btn = document.createElement("button");
        btn.className = "suggestion-button";
        btn.innerText = option.label;

        btn.onclick = () => {
            document.getElementById("message-input").value = option.message;
            sendMessage();
            wrapper.remove();
        };

        wrapper.appendChild(btn);
    });

    chatBox.appendChild(wrapper);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function linkify(text) {
    const escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    return escaped.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer">Open Google Maps</a>'
    );
}

function removeSuggestionBoxes() {
    document.querySelectorAll(".suggestion-box").forEach(box => box.remove());
}

document.getElementById("message-input").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});