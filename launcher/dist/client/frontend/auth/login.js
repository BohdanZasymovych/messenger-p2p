document.querySelector(".login-form").addEventListener("submit", function (event) {
    event.preventDefault();
  
    const email = document.querySelector("input[name='email']").value.trim();
    const password = document.querySelector("input[name='password']").value;
  
    if (!email || !password) {
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
  
    const socket = new WebSocket("ws://localhost:9000");
  
    socket.onerror = (error) => {
      console.error("❌ WebSocket error:", error);
      alert("Failed to connect to server.");
    };
  
    socket.onopen = () => {
      console.log("✅ WebSocket connected");
  
      const loginRequest = {
        type: "get_user_info_from_data_base",
        user_id: "temp", // 👈 Додано для коректності обробки на сервері
        content: {
          email: email,
          password: password
        }
      };
  
      socket.send(JSON.stringify(loginRequest));
      console.log("📤 Sent login request:", loginRequest);
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
  
      if (response.type === "get_user_info_from_data_base_response") {
        if (response.content.status === "success" && response.content.user_exists) {
          console.log("✅ Login successful");
  
          const userId = response.content.user_id;
  
          setTimeout(() => {
            socket.close();
            window.location.href = `../chat/chat.html?user_id=${encodeURIComponent(userId)}&password=${encodeURIComponent(password)}`;
          }, 300);
        } else {
          alert("❌ Login failed: " + (response.content.message || "Incorrect email or password."));
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
  