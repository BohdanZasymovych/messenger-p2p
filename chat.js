let userId = prompt("Enter your user ID:");
let currentTargetUserId = null;

const testChatUserIds = ["alice", "bob", "charlie"]; // ⚠️ додай сюди тестові імена юзерів

async function createChat() {
  const targetUserId = document.getElementById("newChatUserId").value.trim();
  if (!targetUserId) return;

  const res = await fetch("http://127.0.0.1:8000/add_chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, target_user_id: targetUserId })
  });

  if (res.ok) {
    addChatToUI(targetUserId);
    document.getElementById("newChatUserId").value = "";
  } else {
    const err = await res.json();
    alert("❌ " + err.detail);
  }
}

function addChatToUI(targetUserId) {
  const li = document.createElement("li");
  li.textContent = targetUserId;
  li.onclick = () => openChat(targetUserId);
  document.getElementById("chatList").appendChild(li);
}

async function openChat(targetUserId) {
  currentTargetUserId = targetUserId;
  document.getElementById("chatWith").textContent = targetUserId;
  document.getElementById("messages").innerHTML = "";

  const res = await fetch(`http://127.0.0.1:8000/get_messages/${userId}/${targetUserId}`);
  const messages = await res.json();

  messages.forEach(msg => {
    const bubble = document.createElement("div");
    bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
    bubble.textContent = msg.text;
    document.getElementById("messages").appendChild(bubble);
  });
}

async function sendMessage() {
  const input = document.getElementById("messageInput");
  const messageText = input.value.trim();
  if (!messageText || !currentTargetUserId) return;

  const res = await fetch("http://127.0.0.1:8000/send_message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      target_user_id: currentTargetUserId,
      text: messageText,
      timestamp: new Date().toISOString()
    })
  });

  if (res.ok) {
    const bubble = document.createElement("div");
    bubble.classList.add("message", "sent");
    bubble.textContent = messageText;
    document.getElementById("messages").appendChild(bubble);
    input.value = "";
  }
}

function handleKeyPress(event) {
  if (event.key === "Enter") sendMessage();
}

async function loadChats() {
  for (const targetId of testChatUserIds) {
    if (targetId === userId) continue;

    addChatToUI(targetId);

    const res = await fetch(`http://127.0.0.1:8000/get_messages/${userId}/${targetId}`);
    if (!res.ok) continue;
    const messages = await res.json();

    if (!currentTargetUserId) {
      currentTargetUserId = targetId;
      document.getElementById("chatWith").textContent = targetId;
      document.getElementById("messages").innerHTML = "";
      messages.forEach(msg => {
        const bubble = document.createElement("div");
        bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
        bubble.textContent = msg.text;
        document.getElementById("messages").appendChild(bubble);
      });
    }
  }
}

async function loadRegisteredUsers() {
  const res = await fetch("http://127.0.0.1:8000/users");
  const users = await res.json();
  console.log("Registered users:", users); // 👉 можна виводити в UI
}

window.onload = async () => {
  await loadChats();
  await loadRegisteredUsers(); // не обов’язково, але залишив
};
