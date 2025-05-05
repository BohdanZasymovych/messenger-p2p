document.querySelector(".login-form").addEventListener("submit", function (event) {
    event.preventDefault();
  
    const nickname = document.querySelector("input[name='nickname']").value.trim();
    const email = document.querySelector("input[name='email']").value.trim();
    const password = document.querySelector("input[name='password']").value;
  
    if (!nickname || !email || !password) {
      alert("Please fill in all fields.");
      return;
    }
  
    const emailRegex    = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$/;

    if (!emailRegex.test(email)) {
        alert("❌ Please enter a valid email address.");
        return;
    }
    if (!passwordRegex.test(password)) {
        alert("❌ Password must contain at least 8 characters, including uppercase, lowercase, number, and special symbol.");
        return;
    }

    const socket = new WebSocket("wss://messenger-server.fly.dev");
  
    socket.onerror = (error) => {
      console.error("❌ WebSocket error:", error);
      alert("Failed to connect to server.");
    };
  
    socket.onopen = () => {
      console.log("✅ WebSocket connected");
  
      const registerRequest = {
        type: "add_user_to_data_base",
        user_id: nickname,
        content: {
          user_id: nickname,
          email: email,
          password: password
        }
      };
  
      socket.send(JSON.stringify(registerRequest));
      console.log("📤 Sent registration request:", registerRequest);
    };
  
    socket.onmessage = (event) => {
      console.log("📥 Response received:", event.data);
  
      let response;
      try {
        response = JSON.parse(event.data);
      } catch (e) {
        console.error("❌ Failed to parse server response:", e);
        alert("Server returned invalid response.");
        socket.close();
        return;
      }
  
      if (response.type === "add_user_to_data_base_response") {
        if (response.content.status === "success") {
          console.log("✅ User registered successfully");
  
          setTimeout(() => {
            socket.close();
            window.location.href = `../chat/chat.html?user_id=${encodeURIComponent(nickname)}&password=${encodeURIComponent(password)}`;
          }, 300);
        } else {
          alert("❌ Registration failed: " + response.content.message);
          socket.close();
        }
      } else {
        console.warn("ℹ️ Unexpected message type:", response.type);
      }
    };
  
    socket.onclose = () => {
      console.warn("🔌 WebSocket connection closed");
    };
  });
  