let userId = null;
let currentTargetUserId = null;
const lastMessageTimestamps = {};
const lastMessageDates = {};

const userIdFromStorage = sessionStorage.getItem("user_id");
const passwordFromStorage = sessionStorage.getItem("password");

window.onload = () => {
  if (!userIdFromStorage || !passwordFromStorage) {
    alert("Missing user session. Please log in again.");
    window.location.href = "../auth/login.html";
    return;
  }
  login(userIdFromStorage, passwordFromStorage);
};

function login(id, password) {
  const user_id = id;
  const user_password = password;

  fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, password: user_password })
  })
    .then(res => {
      if (!res.ok) throw new Error("Login failed");
      return res.json();
    })
    .then(async () => {
      userId = user_id;
      console.log("✅ Login successful");

      document.querySelector(".sidebar").style.display = "block";
      document.getElementById("chatWindow").style.display = "none";
      document.getElementById("inputBar").style.display = "none";
      document.querySelector(".chat-header").style.display = "none";

      await waitForChatsLoaded();
      await loadChats();
      startMessagePolling();
      startChatPolling();
    })
    .catch(err => {
      console.error("Login error:", err);
      alert("Login failed: " + (err.message || "Unknown error"));
    });
}

async function waitForChatsLoaded() {
  while (true) {
    const res = await fetch("/api/chats_loaded");
    if (!res.ok) throw new Error("Failed to check chats_loaded");
    const { loaded } = await res.json();
    if (loaded) return;
    await new Promise(r => setTimeout(r, 300));
  }
}

async function loadChats() {
  const res = await fetch(`/api/get_chats/${userId}`);
  const chatIds = await res.json();
  chatIds.forEach(addChatToUI);
}

async function createChat() {
  const targetUserId = document.getElementById("newChatUserId").value.trim();
  if (!targetUserId) {
    showNotification("Please enter a user ID");
    return;
  }

  try {
    const res = await fetch("/api/add_chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, target_user_id: targetUserId })
    });
    const data = await res.json();

    if (!res.ok || data.status === "invalid_user_id") {
      showNotification("Invalid user ID entered");
      return;
    }

    addChatToUI(targetUserId);
    await openChat(targetUserId);
    document.getElementById("newChatUserId").value = "";
    document.getElementById("messageInput").focus();

  } catch (err) {
    console.error("Error creating chat:", err);
    showNotification("Failed to create chat");
  }
}

function showNotification(message) {
  const n = document.getElementById("notification");
  if (!n) return;
  n.textContent = message;
  n.classList.add("show");
  setTimeout(() => n.classList.remove("show"), 3000);
}

function addChatToUI(targetUserId) {
  if (document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`)) return;

  const li = document.createElement("li");
  li.textContent = targetUserId;
  li.setAttribute("data-user-id", targetUserId);
  li.onclick = () => openChat(targetUserId);
  document.getElementById("chatList").appendChild(li);
}

async function openChat(targetUserId) {
  currentTargetUserId = targetUserId;

  const chatHeader = document.querySelector(".chat-header");
  const chatWindow = document.getElementById("chatWindow");
  const inputBar = document.getElementById("inputBar");

  if (chatWindow) {
    chatWindow.style.display = "flex";
    chatWindow.style.background = "#0b0b3b";
  }
  if (inputBar) inputBar.style.display = "flex";
  if (chatHeader) chatHeader.style.display = "flex";

  document.getElementById("chatWith").textContent = targetUserId;
  document.getElementById("messages").innerHTML = "";

  const res = await fetch(`/api/get_messages/${userId}/${targetUserId}`);
  const messages = await res.json();

  lastMessageTimestamps[targetUserId] = messages.length
    ? messages[messages.length - 1].timestamp
    : null;

  let currentDate = null;
  messages.forEach(msg => {
    const msgDate = new Date(msg.timestamp);
    const dateStr = formatDate(msgDate);

    if (dateStr !== currentDate) {
      const dateDiv = document.createElement("div");
      dateDiv.classList.add("date-divider");
      dateDiv.textContent = dateStr;
      document.getElementById("messages").appendChild(dateDiv);
      currentDate = dateStr;
    }

    const bubble = document.createElement("div");
    bubble.classList.add("message", msg.sender === userId ? "sent" : "received");
    bubble.textContent = msg.text;

    const timeEl = document.createElement("div");
    timeEl.classList.add("message-time");
    timeEl.textContent = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    bubble.appendChild(timeEl);

    document.getElementById("messages").appendChild(bubble);
  });

  document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
}

function formatDate(date) {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return date.toLocaleDateString();
}

async function sendMessage() {
  const input = document.getElementById("messageInput");
  const text = input.value.trim();
  if (!text || !currentTargetUserId) return;

  const timestamp = new Date().toISOString();

  const res = await fetch("/api/send_message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      target_user_id: currentTargetUserId,
      text,
      timestamp
    })
  });

  if (res.ok) {
    input.value = "";

    const msgDate = new Date(timestamp);
    const dateStr = formatDate(msgDate);

    if (dateStr !== lastMessageDates[currentTargetUserId]) {
      const dateDiv = document.createElement("div");
      dateDiv.classList.add("date-divider");
      dateDiv.textContent = dateStr;
      document.getElementById("messages").appendChild(dateDiv);
      lastMessageDates[currentTargetUserId] = dateStr;
    }

    const bubble = document.createElement("div");
    bubble.classList.add("message", "sent");
    bubble.textContent = text;

    const timeEl = document.createElement("div");
    timeEl.classList.add("message-time");
    timeEl.textContent = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    bubble.appendChild(timeEl);

    document.getElementById("messages").appendChild(bubble);
    document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;

    lastMessageTimestamps[currentTargetUserId] = timestamp;
  } else {
    alert("Failed to send message");
  }
}

function handleKeyPress(e) {
  if (e.key === "Enter") sendMessage();
}

function startMessagePolling() {
  setInterval(pollAllChats, 2000);
}

async function fetchNewMessages(targetUserId) {
  const lastTimestamp = lastMessageTimestamps[targetUserId];
  const url = lastTimestamp
    ? `/api/get_new_messages/${userId}/${targetUserId}/${encodeURIComponent(lastTimestamp)}`
    : `/api/get_messages/${userId}/${targetUserId}`;

  const res = await fetch(url);
  if (!res.ok) return;
  const messages = await res.json();
  if (messages.length === 0) return;

  lastMessageTimestamps[targetUserId] = messages[messages.length - 1].timestamp;

  if (targetUserId === currentTargetUserId) {
    for (const msg of messages) {
      const msgDate = new Date(msg.timestamp);
      const dateStr = formatDate(msgDate);

      if (dateStr !== lastMessageDates[targetUserId]) {
        const dateDiv = document.createElement("div");
        dateDiv.classList.add("date-divider");
        dateDiv.textContent = dateStr;
        document.getElementById("messages").appendChild(dateDiv);
        lastMessageDates[targetUserId] = dateStr;
      }

      const bubble = document.createElement("div");
      bubble.classList.add("message", msg.sender === userId ? "sent" : "received");
      bubble.textContent = msg.text;

      const timeEl = document.createElement("div");
      timeEl.classList.add("message-time");
      timeEl.textContent = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      bubble.appendChild(timeEl);

      document.getElementById("messages").appendChild(bubble);
    }

    document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
  } else {
    const li = document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`);
    if (li && !li.querySelector(".badge")) {
      const badge = document.createElement("span");
      badge.classList.add("badge");
      badge.textContent = "•";
      li.appendChild(badge);
    }
  }
}

async function pollAllChats() {
  const chatIds = Array.from(document.querySelectorAll("#chatList li[data-user-id]"))
    .map(li => li.getAttribute("data-user-id"));
  for (const id of chatIds) await fetchNewMessages(id);
}

function startChatPolling() {
  setInterval(pollNewChats, 2000);
}

async function pollNewChats() {
  const res = await fetch("/api/new_chats");
  if (!res.ok) return;
  const { new_chats } = await res.json();
  new_chats.forEach(id => {
    addChatToUI(id);
  });
}
