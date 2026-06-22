async function sendMessage() {
    const input = document.getElementById("message-input");
    const chatBox = document.getElementById("chat-box");

    const message = input.value.trim();

    if (!message) return;

    appendMessage(message, "user");
    input.value = "";

    appendMessage("Thinking... 🎀", "bot", "loading-message");

    const response = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message })
    });

    const data = await response.json();

    const loading = document.getElementById("loading-message");
    if (loading) loading.remove();

    appendMessage(data.response, "bot");
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
}

document.getElementById("message-input").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});