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


// document.querySelector(".login-form").addEventListener("submit", async function(event) {
//     event.preventDefault();
  
//     const nickname = document.querySelector("input[name='nickname']").value;
//     const email = document.querySelector("input[name='email']").value;
//     const password = document.querySelector("input[name='password']").value;
  
//     const socket = new WebSocket("ws://localhost:8000");
  
//     socket.onopen = () => {
//       const registerRequest = {
//         type: "add_user_to_data_base",
//         user_id: nickname,
//         content: {
//           user_id: nickname,
//           email: email,
//           password: password
//         }
//       };
//       socket.send(JSON.stringify(registerRequest));
//     };
  
//     socket.onmessage = (event) => {
//       const response = JSON.parse(event.data);
//       if (response.type === "add_user_to_data_base_response") {
//         if (response.content.status === "success") {
//           // ✅ Реєстрація успішна — редірект з передачею user_id і password
//           setTimeout(() => {
//             socket.close();
//             window.location.href = `chat.html?user_id=${encodeURIComponent(nickname)}&password=${encodeURIComponent(password)}`;
//           }, 300);
//         } else {
//           alert("❌ Registration failed: " + response.content.message);
//           socket.close();
//         }
//       }
//     };
  
//     socket.onerror = (error) => {
//       console.error("WebSocket error:", error);
//       alert("Connection error.");
//     };
//   });
// const socket = new WebSocket("ws://localhost:9000");

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

//             // Зберігаємо nickname, щоб передати його в chat.html через URL
//             const nickname = document.querySelector("input[name='nickname']").value.trim();

//             setTimeout(() => {
//                 socket.close();
//                 // Перехід на чат з передачею user_id у параметрах
//                 window.location.href = "chat.html?user_id=" + encodeURIComponent(nickname);
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

//     const nickname = document.querySelector("input[name='nickname']").value.trim();
//     const email = document.querySelector("input[name='email']").value.trim();
//     const password = document.querySelector("input[name='password']").value.trim();

//     if (!nickname || !email || !password) {
//         alert("❗ Please fill in all fields!");
//         return;
//     }

//     const request = {
//         type: "add_user_to_data_base",
//         user_id: nickname,
//         content: {
//             user_id: nickname,
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

document.querySelector(".login-form").addEventListener("submit", function (event) {
    event.preventDefault();
  
    const nickname = document.querySelector("input[name='nickname']").value.trim();
    const email = document.querySelector("input[name='email']").value.trim();
    const password = document.querySelector("input[name='password']").value;
  
    if (!nickname || !email || !password) {
      alert("Please fill in all fields.");
      return;
    }
  
    const socket = new WebSocket("ws://localhost:9000");
  
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
            window.location.href = `chat.html?user_id=${encodeURIComponent(nickname)}&password=${encodeURIComponent(password)}`;
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
  