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
    // Set userId and store in localStorage for persistent login
    userId = enteredId;
    // localStorage.setItem('chatUserId', userId);
    
    // Hide login overlay
    document.getElementById("loginOverlay").style.display = "none";
    
    // Show chat interface
    document.querySelector(".sidebar").style.display = "block";
    document.querySelector(".chat-window").style.display = "block";
    document.querySelector(".map-button").style.display = "block";
    
    // Load chat data
    loadChats();
    loadRegisteredUsers();
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

// Poll for new messages every few seconds
function startMessagePolling() {
  setInterval(() => {
      if (userId && currentTargetUserId) {
          fetchNewMessages(currentTargetUserId);
      }
  }, 2000);  // Check every 2 seconds
}

// Fetch new messages for the current chat
async function fetchNewMessages(targetUserId) {
  const res = await fetch(`/api/get_messages/${userId}/${targetUserId}`);
  if (!res.ok) return;
  
  const messages = await res.json();
  
  // Count how many messages we already have displayed
  const existingMessageCount = document.querySelectorAll('.message').length;
  
  // If there are new messages
  if (messages.length > existingMessageCount) {
      // Only display new messages
      for (let i = existingMessageCount; i < messages.length; i++) {
          const msg = messages[i];
          const bubble = document.createElement("div");
          bubble.classList.add("message", msg.sender === "me" ? "sent" : "received");
          bubble.textContent = msg.text;
          document.getElementById("messages").appendChild(bubble);
      }
      
      // Scroll to the bottom
      const messagesContainer = document.getElementById("messages");
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
}

function handleKeyPress(event) {
  if (event.key === "Enter") sendMessage();
}

async function loadChats() {
  // Get actual chats from the backend instead of using testChatUserIds
  const res = await fetch(`/api/get_chats/${userId}`);
  if (!res.ok) {
    console.error("Failed to load chats");
    return;
  }
  
  const chatUserIds = await res.json();
  
  // If no chats, show empty state
  if (chatUserIds.length === 0) {
    document.getElementById("chatWith").textContent = "No chats yet. Add a chat to get started!";
    return;
  }
  
  // Add each chat to the UI
  for (const targetId of chatUserIds) {
    addChatToUI(targetId);
    
    // Try to load messages for this chat
    const msgRes = await fetch(`/api/get_messages/${userId}/${targetId}`);
    if (!msgRes.ok) continue;
    const messages = await msgRes.json();
    
    // If no active chat yet, make this the active chat
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
  const res = await fetch("/api/users");
  const users = await res.json();
  console.log("Registered users:", users); // 👉 можна виводити в UI
}

window.onload = () => {
  // Check if we have a userId stored in localStorage (optional persistent login)
  const storedUserId = localStorage.getItem('chatUserId');
  
  if (storedUserId) {
    // If we have a stored userId, use it and skip login
    userId = storedUserId;
    document.getElementById("loginOverlay").style.display = "none";
    
    // Load chats with the stored userId
    loadChats();
    loadRegisteredUsers();
  } else {
    // No stored userId, show login screen
    document.getElementById("loginOverlay").style.display = "flex";
    
    // Hide the main chat interface elements
    document.querySelector(".sidebar").style.display = "none";
    document.querySelector(".chat-window").style.display = "none";
    document.querySelector(".map-button").style.display = "none";
    
    // Set up login button event (if not already set in HTML)
    document.querySelector("#loginOverlay button").onclick = login;
  }
  
  // Pre-fill the login field with a test ID for easier testing (optional)
  if (!storedUserId) {
    document.getElementById("loginUserId").value = "testuser";
  }

  startMessagePolling();
};