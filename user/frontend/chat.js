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
      document.getElementById("loginOverlay").style.display = "none";
      document.querySelector(".sidebar").style.display = "block";
      document.querySelector(".map-button").style.display = "block";

      (async () => {
        const ok = await waitForChatsLoaded();
        if (!ok) {
          alert("Server didn't finish loading chats in time, please try again.");
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
    console.log("Response from add_chat:", res);
    
    if (res.ok) {
      // Show the chat interface if it was hidden
      document.getElementById("chatWindow").style.display = "flex"; // Changed to flex
      document.getElementById("inputBar").style.display = "flex"; // Show input bar
      
      // Add the chat to UI
      addChatToUI(targetUserId);
      
      // Clear the input field
      document.getElementById("newChatUserId").value = "";
      
      // Open the newly created chat
      await openChat(targetUserId);
      
      // Focus the message input
      document.getElementById("messageInput").focus();
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
    bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
    bubble.textContent = msg.text;
    
    if (msg.timestamp) {
      const timeEl = document.createElement("div");
      timeEl.classList.add("message-time");
      const timeString = msgDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
      timeEl.textContent = timeString;
      bubble.appendChild(timeEl);
    }
    
    document.getElementById("messages").appendChild(bubble);
  });

  const messagesContainer = document.getElementById("messages");
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}


function formatDate(date) {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  
  if (date.toDateString() === today.toDateString()) {
    return "Today";
  }
  
  if (date.toDateString() === yesterday.toDateString()) {
    return "Yesterday";
  }
  
  const options = { day: 'numeric', month: 'long' };
  return date.toLocaleDateString('en-US', options);
}


async function sendMessage() {
  const input = document.getElementById("messageInput");
  const messageText = input.value.trim();
  if (!messageText || !currentTargetUserId) return;

  const timestamp = new Date().toISOString();
  
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

  if (res.ok) {
    const now = new Date();
    const dateStr = formatDate(now);
    
    const lastDivider = document.querySelector(".date-divider:last-of-type");
    const needsNewDivider = !lastDivider || lastDivider.textContent !== dateStr;
    
    if (needsNewDivider) {
      const dateDiv = document.createElement("div");
      dateDiv.classList.add("date-divider");
      dateDiv.textContent = dateStr;
      document.getElementById("messages").appendChild(dateDiv);
    }
    
    const bubble = document.createElement("div");
    bubble.classList.add("message", "sent");
    bubble.textContent = messageText;
    
    const timeEl = document.createElement("div");
    timeEl.classList.add("message-time");
    const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    timeEl.textContent = timeString;
    bubble.appendChild(timeEl);
    
    document.getElementById("messages").appendChild(bubble);
    input.value = "";
    
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

function startNewChatPolling() {
  setInterval(async () => {
    if (!userId) return; // Only poll if user is logged in
    
    try {
      const res = await fetch('/api/new_chats');
      if (!res.ok) return;
      
      const newChatIds = await res.json();
      if (newChatIds.length === 0) return; // No new chats
      
      console.log("New chats detected:", newChatIds);
      
      // Add each new chat to the UI
      for (const chatId of newChatIds) {
        addChatToUI(chatId);
        
        // Show notification for the new chat
        const notification = document.createElement('div');
        notification.classList.add('notification');
        notification.textContent = `New chat from ${chatId}`;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.background = '#4CAF50';
        notification.style.color = 'white';
        notification.style.padding = '10px';
        notification.style.borderRadius = '5px';
        notification.style.zIndex = '1000';
        
        document.body.appendChild(notification);
        
        // Remove the notification after 5 seconds
        setTimeout(() => notification.remove(), 5000);
      }
      
      // If there are no chats shown currently, update the UI
      const chatList = document.getElementById("chatList");
      if (chatList.querySelector('.empty')) {
        loadChats(); // Reload all chats to refresh the UI
      }
    } catch (error) {
      console.error("Error checking for new chats:", error);
    }
  }, 3000); // Check every 3 seconds
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

  const existingCount = (targetUserId === currentTargetUserId)
    ? document.querySelectorAll('#messages .message').length
    : 0;

  if (messages.length <= existingCount) return;

  const newMsgs = messages.slice(existingCount);

  if (targetUserId === currentTargetUserId) {
    const container = document.getElementById('messages');
    newMsgs.forEach(msg => {
      const bubble = document.createElement("div");
      bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
      bubble.textContent = msg.text;
      
      if (msg.timestamp) {
        const timeEl = document.createElement("div");
        timeEl.classList.add("message-time");
        const date = new Date(msg.timestamp);
        const timeString = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        timeEl.textContent = timeString;
        bubble.appendChild(timeEl);
      }
      
      container.appendChild(bubble);
    });
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
    chatList.innerHTML = '<li class="empty">No chats yet. Add a chat to get started!</li>';
    document.getElementById("chatWindow").style.display = "none";
    document.getElementById("inputBar").style.display = "none";
    document.getElementById("chatWith").textContent = "";
    return;
  }

  // Show the chat interface if we have chats
  document.getElementById("chatWindow").style.display = "flex"; // Changed to flex
  document.getElementById("inputBar").style.display = "flex"; // Show input bar

  for (const targetId of chatUserIds) {
    addChatToUI(targetId);
    try {
      const msgRes = await fetch(`/api/get_messages/${userId}/${targetId}`);
      if (!msgRes.ok) continue;
    } catch (error) {
      console.error(`Failed to load messages for ${targetId}:`, error);
    }
  }
}

async function loadRegisteredUsers() {
  const res = await fetch("/api/users");
  const users = await res.json();
  console.log("Registered users:", users);
}

window.onload = () => {
  document.getElementById("loginOverlay").style.display = "flex";
  
  // Hide the main chat interface elements
  document.querySelector(".sidebar").style.display = "none";
  document.getElementById("chatWindow").style.display = "none";
  document.getElementById("inputBar").style.display = "none";
  document.querySelector(".map-button").style.display = "none";
  
  // Set up login button event (if not already set in HTML)
  document.querySelector("#loginOverlay button").onclick = login;

  startMessagePolling();
  startNewChatPolling();
};