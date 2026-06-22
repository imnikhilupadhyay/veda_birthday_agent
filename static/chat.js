async function sendMessage() {
    const input = document.getElementById("message-input");
    const chatBox = document.getElementById("chat-box");

    const message = input.value.trim();

    if (!message) return;

    appendMessage(message, "user");
    input.value = "";

    const botMessage = appendMessage("", "bot");

    const response = await fetch("/chat-stream", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let fullText = "";

    while (true) {
        const { value, done } = await reader.read();

        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullText += chunk;
        botMessage.innerText = fullText;
        chatBox.scrollTop = chatBox.scrollHeight;
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

document.getElementById("message-input").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});