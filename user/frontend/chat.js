let userId = null;
let currentTargetUserId = null;


function login() {
  const enteredId = document.getElementById("loginUserId").value.trim();
  if (!enteredId) {
    alert("Please enter a user ID");
    return;
  }
  
  fetch(`/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: enteredId })
  })
  .then(res => {
    if (!res.ok) {
      throw new Error("Login failed");
    }
    return res.json();
  })
  .then(data => {
    userId = String(enteredId);
    console.log("Login successful, waiting for backend initialization...");

    setTimeout(() => {
      // Hide login overlay
      document.getElementById("loginOverlay").style.display = "none";
      // Show chat interface
      document.querySelector(".sidebar").style.display = "block";
      document.querySelector(".chat-window").style.display = "block";
      document.querySelector(".map-button").style.display = "block";

      (async () => {
        const ok = await waitForChatsLoaded();
        if (!ok) {
          alert("Server didn’t finish loading chats in time, please try again.");
          return;
        }
        await loadChats();
        await loadRegisteredUsers();
      })();
    }, 1000);
  })
  .catch(error => {
    console.error("Login error:", error);
    alert("Login failed: " + (error.message || "Unknown error"));
  });
}

async function createChat() {
  const targetUserId = document.getElementById("newChatUserId").value.trim();
  if (!targetUserId) {
    alert("Please enter a user ID");
    return;
  }
  
  try {
    const res = await fetch("/api/add_chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, target_user_id: targetUserId })
    });
    
    if (res.ok) {
      // Add the chat to UI
      addChatToUI(targetUserId);
      
      // Clear the input field
      document.getElementById("newChatUserId").value = "";
      
      // Open the newly created chat
      await openChat(targetUserId);
    } else {
      const error = await res.json();
      alert(`Failed to create chat: ${error.detail || 'Unknown error'}`);
    }
  } catch (error) {
    alert(`Failed to create chat: ${error.message}`);
  }
}

function addChatToUI(targetUserId) {
  // Check if this chat already exists in the UI
  const existingChat = document.querySelector(`#chatList li[data-user-id="${targetUserId}"]`);
  if (existingChat) return; // Don't add duplicates
  
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

  const res = await fetch(`/api/get_messages/${userId}/${targetUserId}`);
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

  const res = await fetch("/api/send_message", {
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
    
    // Scroll to the bottom after sending
    const messagesContainer = document.getElementById("messages");
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}
}

function startMessagePolling() {
  setInterval(() => {
    if (!userId) return;
    pollAllChats();
  }, 2000);
}

async function pollAllChats() {
  // grab every chatId from the sidebar
  const chatIds = Array.from(
    document.querySelectorAll('#chatList li[data-user-id]')
  ).map(li => li.dataset.userId);

  for (const id of chatIds) {
    await fetchNewMessages(id);
  }
}

async function fetchNewMessages(targetUserId) {
  const res = await fetch(`/api/get_messages/${userId}/${targetUserId}`);
  if (!res.ok) return;
  const messages = await res.json();

  // we only want to append *truly new* messages
  // so count what’s already in memory
  const existingCount = (targetUserId === currentTargetUserId)
    // only count in the visible container
    ? document.querySelectorAll('#messages .message').length
    : (document.querySelectorAll(
         `#chatList li[data-user-id="${targetUserId}"] .badge`
       ).length || 0);

  if (messages.length <= existingCount) return;

  const newMsgs = messages.slice(existingCount);

  if (targetUserId === currentTargetUserId) {
    // if it’s the open chat, render into the pane
    const container = document.getElementById('messages');
    newMsgs.forEach(msg => {
      const bubble = document.createElement("div");
      bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
      bubble.textContent = msg.text;
      container.appendChild(bubble);
    });
    container.scrollTop = container.scrollHeight;
  } else {
    // otherwise mark the chat in the sidebar with a little badge
    let li = document.querySelector(
      `#chatList li[data-user-id="${targetUserId}"]`
    );
    if (li && !li.querySelector('.badge')) {
      const badge = document.createElement('span');
      badge.classList.add('badge');
      badge.textContent = '•';
      li.appendChild(badge);
    }
  }
}

function handleKeyPress(event) {
  if (event.key === "Enter") sendMessage();
}

async function waitForChatsLoaded() {
  const maxAttempts = 20;  // Maximum wait time = 10 seconds
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const res = await fetch('/api/chats_loaded');
    const data = await res.json();
    
    if (data.loaded) {
      console.log("Chats loaded successfully");
      return true;
    }
    
    console.log(`Waiting for chats to load (attempt ${attempt + 1}/${maxAttempts})...`);
    // Wait 500ms before trying again
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  console.warn("Timed out waiting for chats to load");
  return false;
}

async function loadChats() {
  // Add loading indicator
  document.getElementById("chatList").innerHTML = '<li class="loading">Loading chats...</li>';

  // Now fetch the chats that should be loaded
  const res = await fetch(`/api/get_chats/${userId}`);
  if (!res.ok) {
    document.getElementById("chatList").innerHTML = '<li class="error">Failed to load chats</li>';
    console.error("Failed to load chats");
    return;
  }

  const chatUserIds = await res.json();
  console.log("Received chat IDs:", chatUserIds);
  document.getElementById("chatList").innerHTML = '';

  if (chatUserIds.length === 0) {
    const chatList = document.getElementById("chatList");
    // show a placeholder in the sidebar
    chatList.innerHTML = '<li class="empty">No chats yet. Add a chat to get started!</li>';
    // clear the chat header
    document.getElementById("chatWith").textContent = "";
    return;
  }

  for (const targetId of chatUserIds) {
    addChatToUI(targetId);
    try {
      const msgRes = await fetch(`/api/get_messages/${userId}/${targetId}`);
      if (!msgRes.ok) continue;
      // if (!currentTargetUserId) {
      //   await openChat(targetId);
      // }
    } catch (error) {
      console.error(`Failed to load messages for ${targetId}:`, error);
    }
  }
}

async function loadRegisteredUsers() {
  const res = await fetch("/api/users");
  const users = await res.json();
  console.log("Registered users:", users); // 👉 можна виводити в UI
}

window.onload = () => {
  document.getElementById("loginOverlay").style.display = "flex";
  
  // Hide the main chat interface elements
  document.querySelector(".sidebar").style.display = "none";
  document.querySelector(".chat-window").style.display = "none";
  document.querySelector(".map-button").style.display = "none";
  
  // Set up login button event (if not already set in HTML)
  document.querySelector("#loginOverlay button").onclick = login;

  startMessagePolling();
};