// // ✅ ОНОВЛЕНИЙ chat.js (повна версія з авторизацією через URL та всією логікою чатів)

// let userId = null;
// let currentTargetUserId = null;
// const lastMessageTimestamps = {};
// const lastMessageDates = {};

// // Зчитування з URL параметрів після реєстрації
// const urlParams = new URLSearchParams(window.location.search);
// const userIdFromUrl = urlParams.get("user_id");
// const passwordFromUrl = urlParams.get("password");

// if (userIdFromUrl && passwordFromUrl) {
//   login(userIdFromUrl, passwordFromUrl);
// }

// function login(id, password) {
//   const user_id = id || document.getElementById("loginUserId").value.trim();
//   const user_password = password || document.getElementById("loginPassword")?.value?.trim();

//   if (!user_id || !user_password) {
//     alert("Please enter both user ID and password");
//     return;
//   }

//   fetch("/api/login", {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({ user_id, password: user_password })
//   })
//     .then(res => {
//       if (!res.ok) throw new Error("Login failed");
//       return res.json();
//     })
//     .then(data => {
//       userId = user_id;
//       console.log("✅ Login successful");

//       document.getElementById("loginOverlay").style.display = "none";
//       document.querySelector(".sidebar").style.display = "block";
//       document.querySelector(".map-button").style.display = "block";

//       loadChats();
//       startMessagePolling();
//     })
//     .catch(err => {
//       console.error("Login error:", err);
//       alert("Login failed: " + (err.message || "Unknown error"));
//     });
// }

// async function createChat() {
//   const targetUserId = document.getElementById("newChatUserId").value.trim();
//   if (!targetUserId) {
//     alert("Please enter a user ID");
//     return;
//   }

//   try {
//     const res = await fetch("/api/add_chat", {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ user_id: userId, target_user_id: targetUserId })
//     });

//     if (res.ok) {
//       document.getElementById("chatWindow").style.display = "flex";
//       document.getElementById("inputBar").style.display = "flex";
//       addChatToUI(targetUserId);
//       document.getElementById("newChatUserId").value = "";
//       await openChat(targetUserId);
//       document.getElementById("messageInput").focus();
//     } else {
//       const error = await res.json();
//       alert(`Failed to create chat: ${error.detail || 'Unknown error'}`);
//     }
//   } catch (error) {
//     alert(`Failed to create chat: ${error.message}`);
//   }
// }

// function addChatToUI(targetUserId) {
//   const existingChat = document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`);
//   if (existingChat) return;

//   const li = document.createElement("li");
//   li.textContent = targetUserId;
//   li.setAttribute("data-user-id", targetUserId);
//   li.onclick = () => openChat(targetUserId);
//   document.getElementById("chatList").appendChild(li);
// }

// async function openChat(targetUserId) {
//   currentTargetUserId = targetUserId;
//   document.getElementById("chatWith").textContent = targetUserId;
//   document.getElementById("messages").innerHTML = "";
//   lastMessageTimestamps[targetUserId] = null;
//   lastMessageDates[targetUserId] = null;

//   const res = await fetch(`/api/get_messages/${userId}/${targetUserId}`);
//   const messages = await res.json();

//   if (messages.length > 0) {
//     lastMessageTimestamps[targetUserId] = messages[messages.length - 1].timestamp;
//   }

//   let currentDate = null;
//   messages.forEach(msg => {
//     const msgDate = new Date(msg.timestamp);
//     const dateStr = formatDate(msgDate);

//     if (dateStr !== currentDate) {
//       const dateDiv = document.createElement("div");
//       dateDiv.classList.add("date-divider");
//       dateDiv.textContent = dateStr;
//       document.getElementById("messages").appendChild(dateDiv);
//       currentDate = dateStr;
//       lastMessageDates[targetUserId] = dateStr;
//     }

//     const bubble = document.createElement("div");
//     bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
//     bubble.textContent = msg.text;

//     const timeEl = document.createElement("div");
//     timeEl.classList.add("message-time");
//     timeEl.textContent = msgDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
//     bubble.appendChild(timeEl);

//     document.getElementById("messages").appendChild(bubble);
//   });

//   document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;

//   const badge = document.querySelector(`#chatList li[data-user-id="${targetUserId}"] .badge`);
//   if (badge) badge.remove();

//   document.getElementById("chatWindow").style.display = "flex";
//   document.getElementById("inputBar").style.display = "flex";
// }

// function formatDate(date) {
//   const today = new Date();
//   const yesterday = new Date(today);
//   yesterday.setDate(today.getDate() - 1);

//   if (date.toDateString() === today.toDateString()) return "Today";
//   if (date.toDateString() === yesterday.toDateString()) return "Yesterday";

//   return date.toLocaleDateString('en-US', { day: 'numeric', month: 'long' });
// }

// async function sendMessage() {
//   const input = document.getElementById("messageInput");
//   const messageText = input.value.trim();
//   if (!messageText || !currentTargetUserId) return;

//   const now = new Date();
//   const timestamp = now.toISOString();

//   const res = await fetch("/api/send_message", {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({
//       user_id: userId,
//       target_user_id: currentTargetUserId,
//       text: messageText,
//       timestamp: timestamp
//     })
//   });

//   if (!res.ok) {
//     alert("Failed to send message");
//     return;
//   }

//   const dateStr = formatDate(now);
//   const messagesContainer = document.getElementById("messages");

//   if (dateStr !== lastMessageDates[currentTargetUserId]) {
//     const dateDiv = document.createElement("div");
//     dateDiv.classList.add("date-divider");
//     dateDiv.textContent = dateStr;
//     messagesContainer.appendChild(dateDiv);
//     lastMessageDates[currentTargetUserId] = dateStr;
//   }

//   const bubble = document.createElement("div");
//   bubble.classList.add("message", "sent");
//   bubble.textContent = messageText;

//   const timeEl = document.createElement("div");
//   timeEl.classList.add("message-time");
//   timeEl.textContent = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
//   bubble.appendChild(timeEl);

//   messagesContainer.appendChild(bubble);
//   input.value = "";
//   lastMessageTimestamps[currentTargetUserId] = timestamp;
//   messagesContainer.scrollTop = messagesContainer.scrollHeight;
// }

// function startMessagePolling() {
//   setInterval(() => {
//     if (!userId) return;
//     pollAllChats();
//   }, 2000);
// }

// async function pollAllChats() {
//   const chatIds = Array.from(
//     document.querySelectorAll('#chatList li[data-user-id]')
//   ).map(li => li.dataset.userId);

//   for (const id of chatIds) {
//     await fetchNewMessages(id);
//   }
// }

// async function fetchNewMessages(targetUserId) {
//   if (!targetUserId || !userId) return;

//   try {
//     const lastTimestamp = lastMessageTimestamps[targetUserId];
//     let url = `/api/get_messages/${userId}/${targetUserId}`;
//     if (lastTimestamp) {
//       url = `/api/get_new_messages/${userId}/${targetUserId}/${encodeURIComponent(lastTimestamp)}`;
//     }

//     const res = await fetch(url);
//     if (!res.ok) return;

//     const messages = await res.json();
//     if (messages.length === 0) return;

//     lastMessageTimestamps[targetUserId] = messages[messages.length - 1].timestamp;

//     if (targetUserId === currentTargetUserId) {
//       const container = document.getElementById("messages");

//       for (const msg of messages) {
//         const msgDate = new Date(msg.timestamp);
//         const dateStr = formatDate(msgDate);

//         if (dateStr !== lastMessageDates[targetUserId]) {
//           const dateDiv = document.createElement("div");
//           dateDiv.classList.add("date-divider");
//           dateDiv.textContent = dateStr;
//           container.appendChild(dateDiv);
//           lastMessageDates[targetUserId] = dateStr;
//         }

//         const bubble = document.createElement("div");
//         bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
//         bubble.textContent = msg.text;

//         const timeEl = document.createElement("div");
//         timeEl.classList.add("message-time");
//         timeEl.textContent = msgDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
//         bubble.appendChild(timeEl);

//         container.appendChild(bubble);
//       }

//       container.scrollTop = container.scrollHeight;
//     } else {
//       let li = document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`);
//       if (li && !li.querySelector('.badge')) {
//         const badge = document.createElement('span');
//         badge.classList.add('badge');
//         badge.textContent = '•';
//         li.appendChild(badge);
//       }
//     }
//   } catch (error) {
//     console.error("Error fetching new messages:", error);
//   }
// }

// function handleKeyPress(event) {
//   if (event.key === "Enter") sendMessage();
// }

// window.onload = () => {
//   document.getElementById("loginOverlay").style.display = "flex";
//   document.querySelector(".sidebar").style.display = "none";
//   document.getElementById("chatWindow").style.display = "none";
//   document.getElementById("inputBar").style.display = "none";
//   document.querySelector(".map-button").style.display = "none";
//   document.querySelector("#loginOverlay button").onclick = login;
//   startMessagePolling();
// };


let userId = null;
let currentTargetUserId = null;
const lastMessageTimestamps = {};
const lastMessageDates = {};

// Зчитування з URL параметрів після реєстрації
const urlParams = new URLSearchParams(window.location.search);
const userIdFromUrl = urlParams.get("user_id");
const passwordFromUrl = urlParams.get("password");

if (userIdFromUrl && passwordFromUrl) {
  login(userIdFromUrl, passwordFromUrl);
}

function login(id, password) {
  const user_id = id || document.getElementById("loginUserId").value.trim();
  const user_password = password || document.getElementById("loginPassword")?.value?.trim();

  if (!user_id || !user_password) {
    alert("Please enter both user ID and password");
    return;
  }

  fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, password: user_password })
  })
    .then(res => {
      if (!res.ok) throw new Error("Login failed");
      return res.json();
    })
    .then(data => {
      userId = user_id;
      console.log("✅ Login successful");

      document.getElementById("loginOverlay").style.display = "none";
      document.querySelector(".sidebar").style.display = "block";
      document.querySelector(".map-button").style.display = "block";

      loadChats();
      startMessagePolling();
    })
    .catch(err => {
      console.error("Login error:", err);
      alert("Login failed: " + (err.message || "Unknown error"));
    });
}

async function createChat() {
  const targetUserId = document.getElementById("newChatUserId").value.trim();
  if (!targetUserId) {
    alert("Please enter a user ID");
    return;
  }

  let success = false;

  try {
    const res = await fetch("/api/add_chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, target_user_id: targetUserId })
    });

    success = res.ok;
    if (!success) {
      const error = await res.json();
      console.warn(`Backend failed to create chat: ${error.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.warn(`Fetch error while creating chat: ${error.message}`);
  }

  // Even if chat creation failed, still show it visually
  addChatToUI(targetUserId);
  document.getElementById("chatWindow").style.display = "flex";
  document.getElementById("inputBar").style.display = "flex";
  document.getElementById("newChatUserId").value = "";
  await openChat(targetUserId);
  document.getElementById("messageInput").focus();

  if (!success) {
    alert("Chat couldn't be created on server, but it was added visually for testing.");
  }
}

function addChatToUI(targetUserId) {
  const existingChat = document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`);
  if (existingChat) return;

  const li = document.createElement("li");
  li.textContent = targetUserId;
  li.setAttribute("data-user-id", targetUserId);
  li.onclick = () => openChat(targetUserId);
  document.getElementById("chatList").appendChild(li);
}

async function openChat(targetUserId) {
  currentTargetUserId = targetUserId;
  document.getElementById("chatWith").textContent = targetUserId;
  document.getElementById("messages").innerHTML = "";
  lastMessageTimestamps[targetUserId] = null;
  lastMessageDates[targetUserId] = null;

  try {
    const res = await fetch(`/api/get_messages/${userId}/${targetUserId}`);
    if (!res.ok) throw new Error("Could not load messages");

    const messages = await res.json();

    if (messages.length > 0) {
      lastMessageTimestamps[targetUserId] = messages[messages.length - 1].timestamp;
    }

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
        lastMessageDates[targetUserId] = dateStr;
      }

      const bubble = document.createElement("div");
      bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
      bubble.textContent = msg.text;

      const timeEl = document.createElement("div");
      timeEl.classList.add("message-time");
      timeEl.textContent = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      bubble.appendChild(timeEl);

      document.getElementById("messages").appendChild(bubble);
    });

    document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;

    const badge = document.querySelector(`#chatList li[data-user-id="${targetUserId}"] .badge`);
    if (badge) badge.remove();
  } catch (err) {
    console.warn("Failed to load messages (may be fake chat):", err.message);
  }

  document.getElementById("chatWindow").style.display = "flex";
  document.getElementById("inputBar").style.display = "flex";
}

function formatDate(date) {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";

  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'long' });
}

async function sendMessage() {
  const input = document.getElementById("messageInput");
  const messageText = input.value.trim();
  if (!messageText || !currentTargetUserId) return;

  const now = new Date();
  const timestamp = now.toISOString();

  const res = await fetch("/api/send_message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      target_user_id: currentTargetUserId,
      text: messageText,
      timestamp: timestamp
    })
  });

  if (!res.ok) {
    alert("Failed to send message");
    return;
  }

  const dateStr = formatDate(now);
  const messagesContainer = document.getElementById("messages");

  if (dateStr !== lastMessageDates[currentTargetUserId]) {
    const dateDiv = document.createElement("div");
    dateDiv.classList.add("date-divider");
    dateDiv.textContent = dateStr;
    messagesContainer.appendChild(dateDiv);
    lastMessageDates[currentTargetUserId] = dateStr;
  }

  const bubble = document.createElement("div");
  bubble.classList.add("message", "sent");
  bubble.textContent = messageText;

  const timeEl = document.createElement("div");
  timeEl.classList.add("message-time");
  timeEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  bubble.appendChild(timeEl);

  messagesContainer.appendChild(bubble);
  input.value = "";
  lastMessageTimestamps[currentTargetUserId] = timestamp;
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function startMessagePolling() {
  setInterval(() => {
    if (!userId) return;
    pollAllChats();
  }, 2000);
}

async function pollAllChats() {
  const chatIds = Array.from(
    document.querySelectorAll('#chatList li[data-user-id]')
  ).map(li => li.dataset.userId);

  for (const id of chatIds) {
    await fetchNewMessages(id);
  }
}

async function fetchNewMessages(targetUserId) {
  if (!targetUserId || !userId) return;

  try {
    const lastTimestamp = lastMessageTimestamps[targetUserId];
    let url = `/api/get_messages/${userId}/${targetUserId}`;
    if (lastTimestamp) {
      url = `/api/get_new_messages/${userId}/${targetUserId}/${encodeURIComponent(lastTimestamp)}`;
    }

    const res = await fetch(url);
    if (!res.ok) return;

    const messages = await res.json();
    if (messages.length === 0) return;

    lastMessageTimestamps[targetUserId] = messages[messages.length - 1].timestamp;

    if (targetUserId === currentTargetUserId) {
      const container = document.getElementById("messages");

      for (const msg of messages) {
        const msgDate = new Date(msg.timestamp);
        const dateStr = formatDate(msgDate);

        if (dateStr !== lastMessageDates[targetUserId]) {
          const dateDiv = document.createElement("div");
          dateDiv.classList.add("date-divider");
          dateDiv.textContent = dateStr;
          container.appendChild(dateDiv);
          lastMessageDates[targetUserId] = dateStr;
        }

        const bubble = document.createElement("div");
        bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
        bubble.textContent = msg.text;

        const timeEl = document.createElement("div");
        timeEl.classList.add("message-time");
        timeEl.textContent = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        bubble.appendChild(timeEl);

        container.appendChild(bubble);
      }

      container.scrollTop = container.scrollHeight;
    } else {
      let li = document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`);
      if (li && !li.querySelector('.badge')) {
        const badge = document.createElement('span');
        badge.classList.add('badge');
        badge.textContent = '•';
        li.appendChild(badge);
      }
    }
  } catch (err) {
    console.warn("Polling error:", err.message);
  }
}