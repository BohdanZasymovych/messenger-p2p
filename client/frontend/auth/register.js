// const socket = new WebSocket("ws://localhost:8000");

// socket.onopen = () => {
//     console.log("✅ WebSocket connected");
// };

// // Отримуємо повідомлення від сервера
// socket.onmessage = (event) => {
//     console.log("📥 Response received:", event.data);
//     const response = JSON.parse(event.data);

//     if (response.type === "add_user_to_data_base_response") {
//         if (response.content.status === "success") {
//             console.log("✅ User added. Redirecting...");

//             // ⏳ Даемо серверу трохи часу перед закриттям з'єднання
//             setTimeout(() => {
//                 socket.close();
//                 window.location.href = "chat.html";
//             }, 300);
//         } else {
//             alert("❌ Registration failed: " + response.content.message);
//             socket.close();
//         }
//     }
// };

// socket.onerror = (error) => {
//     console.error("❌ WebSocket error:", error);
// };

// socket.onclose = () => {
//     console.warn("🔌 WebSocket connection closed");
// };

// // Обробка форми реєстрації
// document.querySelector(".login-form").addEventListener("submit", async (e) => {
//     e.preventDefault();

//     const nickname = document.querySelector("input[name='nickname']").value;
//     const email = document.querySelector("input[name='email']").value;
//     const password = document.querySelector("input[name='password']").value;

//     const request = {
//         type: "add_user_to_data_base",
//         user_id: nickname,
//         content: {
//             username: nickname,
//             email: email,
//             password: password
//         }
//     };

//     if (socket.readyState === WebSocket.OPEN) {
//         socket.send(JSON.stringify(request));
//         console.log("📤 Sent request:", request);
//     } else {
//         socket.addEventListener("open", () => {
//             socket.send(JSON.stringify(request));
//             console.log("📤 Sent request after open:", request);
//         });
//     }
// });


document.querySelector(".login-form").addEventListener("submit", async function(event) {
    event.preventDefault();
  
    const nickname = document.querySelector("input[name='nickname']").value;
    const email = document.querySelector("input[name='email']").value;
    const password = document.querySelector("input[name='password']").value;
  
    const socket = new WebSocket("ws://localhost:8000");
  
    socket.onopen = () => {
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
    };
  
    socket.onmessage = (event) => {
      const response = JSON.parse(event.data);
      if (response.type === "add_user_to_data_base_response") {
        if (response.content.status === "success") {
          // ✅ Реєстрація успішна — редірект з передачею user_id і password
          setTimeout(() => {
            socket.close();
            window.location.href = `chat.html?user_id=${encodeURIComponent(nickname)}&password=${encodeURIComponent(password)}`;
          }, 300);
        } else {
          alert("❌ Registration failed: " + response.content.message);
          socket.close();
        }
      }
    };
  
    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      alert("Connection error.");
    };
  });
  