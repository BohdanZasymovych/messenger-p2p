document.querySelector(".login-form").addEventListener("submit", async function (event) {
  event.preventDefault();

  const nickname = document.querySelector("input[name='nickname']").value.trim();
  const email = document.querySelector("input[name='email']").value.trim();
  const password = document.querySelector("input[name='password']").value;

  if (!nickname || !email || !password) {
    alert("Please fill in all fields.");
    return;
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$/;

  if (!emailRegex.test(email)) {
    alert("❌ Please enter a valid email address.");
    return;
  }

  if (!passwordRegex.test(password)) {
    alert("❌ Password must contain at least 8 characters, including uppercase, lowercase, number, and special symbol.");
    return;
  }

  // 🛡️ Хешуємо пароль
  const hashedPassword = await hashPasswordSHA256(password);

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
        password: hashedPassword
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

        sessionStorage.setItem("user_id", nickname);
        sessionStorage.setItem("password", password); // незахешований — потрібен для шифрування

        setTimeout(() => {
          socket.close();
          window.location.href = "../chat/chat.html";
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

async function hashPasswordSHA256(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
