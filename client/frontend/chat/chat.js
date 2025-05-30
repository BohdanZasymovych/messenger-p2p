let userId = null;
let currentTargetUserId = null;
let initialLoadComplete = false;

let messagePollingInterval;
let chatPollingInterval;
const lastMessageTimestamps = {};
const lastMessageDates = {};
const lastReadTimestamps = {};

const userIdFromStorage = sessionStorage.getItem("user_id");
const passwordFromStorage = sessionStorage.getItem("password");

function addDateDivider(dateStr, container) {
  const dateDiv = document.createElement("div");
  dateDiv.classList.add("date-divider");
  
  const dateSpan = document.createElement("span");
  dateSpan.textContent = dateStr;
  dateDiv.appendChild(dateSpan);
  
  container.appendChild(dateDiv);
  return dateDiv;
}

// Функція для визначення, чи потрібно додавати роздільник дати
function shouldAddDateDivider(messages, dateStr) {
  // Якщо немає повідомлень, то це перший роздільник
  if (!messages || messages.length === 0) {
    return true;
  }

  // Перевіряємо всі повідомлення знизу вгору
  // щоб знайти останній роздільник дати
  const messagesContainer = document.getElementById("messages");
  const dividers = messagesContainer.querySelectorAll(".date-divider");
  
  if (dividers.length > 0) {
    // Отримуємо текст останнього доданого роздільника
    const lastDivider = dividers[dividers.length - 1];
    const lastDividerText = lastDivider.querySelector("span").textContent;
    
    // Якщо роздільник з такою датою вже є, не додаємо новий
    return lastDividerText !== dateStr;
  }
  
  return true;
}

// Додайте цю функцію для ініціалізації lastMessageDates з локального сховища
function initLastMessageDates() {
  const keys = Object.keys(localStorage);
  for (const key of keys) {
    if (key.startsWith('lastDate_')) {
      const parts = key.split('_');
      if (parts.length >= 3) {
        const targetUserId = parts[2];
        lastMessageDates[targetUserId] = localStorage.getItem(key);
      }
    }
  }
}

function createConsistentTimestamp() {
  return new Date().toISOString();
}

function parseTimestamp(timestamp) {
  try {
    return new Date(timestamp);
  } catch (e) {
    console.error("Failed to parse timestamp:", timestamp);
    return new Date(); // Fallback to current time
  }
}

window.onload = async () => {
  if (!userIdFromStorage || !passwordFromStorage) {
    alert("Missing user session. Please log in again.");
    window.location.href = "../auth/login.html";
    return;
  }
  await login(userIdFromStorage, passwordFromStorage);
  initialLoadComplete = true;
};

function hashPassword(password) {
  return new Promise(resolve => {
    // Import the js-sha256 library if not already present
    if (typeof sha256 === 'undefined') {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/js-sha256/0.9.0/sha256.min.js';
      script.onload = () => {
        resolve(sha256(password));
      };
      document.head.appendChild(script);
    } else {
      resolve(sha256(password));
    }
  });
}

async function login(id, password) {
  const user_id = id;
  const hashedPassword = await hashPassword(password);

  fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, password: hashedPassword})
  })
    .then(res => {
      if (!res.ok) throw new Error("Login failed");
      return res.json();
    })
    .then(async () => {
      userId = user_id;
      console.log("✅ Login successful");

      document.querySelector(".sidebar").style.display = "block";
      // document.getElementById("chatWindow").style.display = "none";
      document.getElementById("chatWindow").style.display = "flex";
      document.getElementById("inputBar").style.display = "none";
      document.querySelector(".chat-header").style.display = "none";

      const ph = document.getElementById("noChatPlaceholder");
      if (ph) ph.style.display = "block";

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

document.addEventListener('DOMContentLoaded', () => {
  // Find the close button and attach the event listener
  const closeButton = document.querySelector('.close-button');
  if (closeButton) {
    closeButton.addEventListener('click', closeApplication);
  }
  
  initLastMessageDates();
});

// Function to handle application closing
function closeApplication() {
  showNotification("Closing application...");
  
  // Send close request to backend
  fetch("/api/close_application", {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  })
  .then(res => {
    if (!res.ok) throw new Error("Failed to close application");
    return res.json();
  })
  .then(() => {
    console.log("Application closing...");
    
    // Stop all polling intervals
    if (window.messagePollingInterval) clearInterval(window.messagePollingInterval);
    if (window.chatPollingInterval) clearInterval(window.chatPollingInterval);
    
    // Clear session data
    sessionStorage.removeItem("user_id");
    sessionStorage.removeItem("password");
    
    // Give server time to process the close request
    setTimeout(() => {
      window.location.href = "../close-page/close_page.html";
    }, 1000);
  })
  .catch(err => {
    console.error("Error closing application:", err);
    showNotification("Failed to close application");
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

  const ph = document.getElementById("noChatPlaceholder");
  if (ph && chatIds.length === 0) {
    ph.style.display = "block";
  }
}

async function createChat() {
  const targetUserId = document.getElementById("newChatUserId").value.trim();
  if (!targetUserId) {
    showNotification("Please enter a user ID");
    return;
  }

  if (document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`)) {
    showNotification("Chat already exists");
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
  const ph = document.getElementById("noChatPlaceholder");
  if (ph) ph.style.display = "none";

  // remove any existing dot for this chat (marks it read)
  const li = document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`);
  if (li) {
    const dot = li.querySelector(".unread-dot");
    if (dot) dot.remove();
  }

  lastReadTimestamps[targetUserId] = Date.now();

  currentTargetUserId = targetUserId;

  const chatHeader = document.querySelector(".chat-header");
  const chatWindow = document.getElementById("chatWindow");
  const inputBar = document.getElementById("inputBar");

  if (chatWindow) {
    chatWindow.style.display = "flex";
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

  const messagesContainer = document.getElementById("messages");
  let currentDate = null;
  let firstDayDividerAdded = false;

  messages.forEach(msg => {
    const msgDate = parseTimestamp(msg.timestamp);
    const dateStr = formatDate(msgDate);

    // Додаємо роздільник дат, якщо змінилася дата
    if (dateStr !== currentDate) {
      // Перевіряємо, чи треба додавати роздільник
      const shouldAdd = shouldAddDateDivider(messagesContainer.querySelectorAll(".message"), dateStr);
      if (shouldAdd) {
        addDateDivider(dateStr, messagesContainer);
      }
      currentDate = dateStr;
      lastMessageDates[targetUserId] = dateStr;
      
      // Запам'ятовуємо, що ми вже додали роздільник для першого дня
      if (!firstDayDividerAdded) {
        firstDayDividerAdded = true;
        // Зберігаємо в локальному сховищі дату останнього повідомлення
        localStorage.setItem(`lastDate_${userId}_${targetUserId}`, dateStr);
      }
    }

    const bubble = document.createElement("div");
    bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
    bubble.textContent = msg.text;

    const timeEl = document.createElement("div");
    timeEl.classList.add("message-time");
    timeEl.textContent = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    bubble.appendChild(timeEl);

    messagesContainer.appendChild(bubble);
  });

  messagesContainer.scrollTop = messagesContainer.scrollHeight;
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

  const timestamp = createConsistentTimestamp();

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

    const msgDate = parseTimestamp(timestamp);
    const dateStr = formatDate(msgDate);
    const messagesContainer = document.getElementById("messages");

    // Перевіряємо, чи потрібно додавати роздільник
    if (dateStr !== lastMessageDates[currentTargetUserId]) {
      const shouldAdd = shouldAddDateDivider(messagesContainer.querySelectorAll(".message"), dateStr);
      if (shouldAdd) {
        addDateDivider(dateStr, messagesContainer);
      }
      lastMessageDates[currentTargetUserId] = dateStr;
      
      // Оновлюємо дату в локальному сховищі
      localStorage.setItem(`lastDate_${userId}_${currentTargetUserId}`, dateStr);
    }

    const bubble = document.createElement("div");
    bubble.classList.add("message", "sent");
    bubble.textContent = text;

    const timeEl = document.createElement("div");
    timeEl.classList.add("message-time");
    timeEl.textContent = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    bubble.appendChild(timeEl);

    messagesContainer.appendChild(bubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    lastMessageTimestamps[currentTargetUserId] = timestamp;
  } else {
    alert("Failed to send message");
  }
}

function handleKeyPress(e) {
  if (e.key === "Enter") sendMessage();
}

function startMessagePolling() {
  window.messagePollingInterval = setInterval(pollAllChats, 2000);
}

async function fetchNewMessages(targetUserId) {
  const lastTimestamp = lastMessageTimestamps[targetUserId];
  
  const url = lastTimestamp
    ? `/api/get_new_messages/${userId}/${targetUserId}/${encodeURIComponent(lastTimestamp)}`
    : `/api/get_messages/${userId}/${targetUserId}`;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.error(`Failed to fetch messages: ${res.status}`);
      return;
    }
    
    const messages = await res.json();
    if (!messages || messages.length === 0) return;
    
    const lastMessageInBatch = messages[messages.length - 1];
    if (lastMessageInBatch && lastMessageInBatch.timestamp) {
      lastMessageTimestamps[targetUserId] = lastMessageInBatch.timestamp;
    }
    
    if (targetUserId === currentTargetUserId) {
      const messagesContainer = document.getElementById("messages");
      
      for (const msg of messages) {
        const msgDate = parseTimestamp(msg.timestamp);
        const dateStr = formatDate(msgDate);

        if (dateStr !== lastMessageDates[targetUserId]) {
          const shouldAdd = shouldAddDateDivider(messagesContainer.querySelectorAll(".message"), dateStr);
          if (shouldAdd) {
            addDateDivider(dateStr, messagesContainer);
          }
          lastMessageDates[targetUserId] = dateStr;
          
          localStorage.setItem(`lastDate_${userId}_${targetUserId}`, dateStr);
        }

        const bubble = document.createElement("div");
        bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
        bubble.textContent = msg.text;

        const timeEl = document.createElement("div");
        timeEl.classList.add("message-time");
        timeEl.textContent = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        bubble.appendChild(timeEl);

        messagesContainer.appendChild(bubble);
      }

      messagesContainer.scrollTop = messagesContainer.scrollHeight;
      
      lastReadTimestamps[targetUserId] = Date.now();
    } else {
      if (initialLoadComplete && lastTimestamp) {
        const li = document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`);
        if (li && !li.querySelector(".unread-dot")) {
          const dot = document.createElement("span");
          dot.classList.add("unread-dot");
          li.appendChild(dot);
        }
      }
    }
  } catch (error) {
    console.error(`Error fetching new messages for ${targetUserId}:`, error);
  }
}

async function pollAllChats() {
  const chatIds = Array.from(document.querySelectorAll("#chatList li[data-user-id]"))
    .map(li => li.getAttribute("data-user-id"));
  for (const id of chatIds) await fetchNewMessages(id);
}

function startChatPolling() {
  window.chatPollingInterval = setInterval(pollNewChats, 2000);
}

async function pollNewChats() {
  const res = await fetch("/api/new_chats");
  if (!res.ok) return;
  const { new_chats } = await res.json();
  new_chats.forEach(id => {
    addChatToUI(id);
  });
}
