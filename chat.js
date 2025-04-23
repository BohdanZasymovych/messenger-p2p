async function sendMessage() {
  const input = document.getElementById('messageInput');
  const messageText = input.value.trim();
  if (!messageText) return;

  // Display the message immediately in UI
  const messageBubble = document.createElement('div');
  messageBubble.classList.add('message', 'sent');
  messageBubble.textContent = messageText;
  document.getElementById('messages').appendChild(messageBubble);

  // Send to backend
  const response = await fetch("http://127.0.0.1:8000/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sender: "me",
      text: messageText,
      timestamp: new Date().toISOString()
    })
  });

  if (response.ok) {
    console.log("✅ Message sent successfully");
  } else {
    console.error("❌ Failed to send message:", await response.text());
  }

  input.value = '';
}

// Handles Enter key in input box
function handleKeyPress(event) {
  if (event.key === 'Enter') {
    sendMessage();
  }
}

// Loads all messages from backend
async function loadMessages() {
  try {
    const res = await fetch("http://127.0.0.1:8000/messages");
    const data = await res.json();
    const container = document.getElementById('messages');
    container.innerHTML = "";

    for (const [sender, messages] of Object.entries(data)) {
      messages.forEach(msg => {
        const bubble = document.createElement('div');
        bubble.classList.add('message', sender === "me" ? 'sent' : 'received');
        bubble.textContent = msg.text;
        container.appendChild(bubble);
      });
    }
  } catch (error) {
    console.error("❌ Failed to load messages:", error);
  }
}

// Load messages when page loads
window.onload = loadMessages;