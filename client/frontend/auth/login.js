const socket = new WebSocket("ws://localhost:9000");

socket.onopen = () => {
    console.log("✅ WebSocket connected");
};

// Обробка відповідей від сервера
socket.onmessage = (event) => {
    console.log("📥 Response received:", event.data);
    const response = JSON.parse(event.data);

    if (response.type === "get_user_info_from_data_base_response") {
        if (response.content.status === "success" && response.content.user_exists) {
            console.log("✅ Login successful. Redirecting...");
            setTimeout(() => {
                socket.close();
                window.location.href = "chat.html";
            }, 300);
        } else {
            alert("❌ Login failed: " + (response.content.message || "Incorrect login credentials."));
            socket.close();
        }
    }
};

socket.onerror = (error) => {
    console.error("❌ WebSocket error:", error);
};

socket.onclose = () => {
    console.warn("🔌 WebSocket connection closed");
};

// Обробка форми логіну
document.querySelector(".login-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const nickname = document.querySelector("input[name='nickname']").value;
    const email = document.querySelector("input[name='email']").value;
    const password = document.querySelector("input[name='password']").value;

    const request = {
        type: "get_user_info_from_data_base",
        user_id: nickname, // 🔑 Обов’язково передаємо user_id
        content: {
            username: nickname,
            email: email,
            password: password
        }
    };

    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(request));
        console.log("📤 Sent login request:", request);
    } else {
        socket.addEventListener("open", () => {
            socket.send(JSON.stringify(request));
            console.log("📤 Sent login request after open:", request);
        });
    }
});
