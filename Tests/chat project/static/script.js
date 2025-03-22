document.addEventListener("DOMContentLoaded", function () {
  // DOM Elements
  const userListView = document.getElementById("userListView");
  const chatView = document.getElementById("chatView");
  const userList = document.getElementById("userList");
  const searchInput = document.getElementById("searchInput");
  const backButton = document.getElementById("backButton");
  const chatAvatar = document.getElementById("chatAvatar");
  const chatUsername = document.getElementById("chatUsername");
  const chatOnlineIndicator = document.getElementById("chatOnlineIndicator");
  const messageList = document.getElementById("messageList");
  const messageInput = document.getElementById("messageInput");
  const sendButton = document.getElementById("sendButton");

  // Application state
  let currentUser = null;
  let users = [];
  let selectedUser = null;
  let currentMessages = {};

  // Connect to WebSocket server
  const socket = io();

  // Socket event handlers
  socket.on("connect", () => {
    console.log("Connected to server");
  });

  socket.on("user_list", (usersList) => {
    users = usersList;

    // Find current user
    currentUser = users.find((user) => user.session_id === socket.id);

    // Update user list UI
    renderUserList();
  });

  socket.on("message_history", (data) => {
    const { room_id, messages } = data;
    currentMessages[room_id] = messages;
    renderMessages(messages);
  });

  socket.on("new_message", (data) => {
    const { room_id, message } = data;

    // Initialize message array if it doesn't exist
    if (!currentMessages[room_id]) {
      currentMessages[room_id] = [];
    }

    // Add new message
    currentMessages[room_id].push(message);

    // If this room is currently open, render the new message
    if (selectedUser && isCorrectRoom(room_id)) {
      renderMessages(currentMessages[room_id]);
    }
  });

  // UI Event Listeners
  searchInput.addEventListener("input", () => {
    renderUserList();
  });

  backButton.addEventListener("click", () => {
    showUserList();
  });

  sendButton.addEventListener("click", sendMessage);

  messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  });

  // Helper Functions
  function renderUserList() {
    // Clear current list
    userList.innerHTML = "";

    // Filter users based on search
    const searchQuery = searchInput.value.toLowerCase();
    const filteredUsers = users.filter(
      (user) =>
        user.id !== currentUser.id &&
        user.name.toLowerCase().includes(searchQuery),
    );

    // Create user items
    filteredUsers.forEach((user) => {
      const userItem = document.createElement("li");
      userItem.className = "user-item";
      userItem.innerHTML = `
                <img src="${user.avatar}" class="user-avatar" alt="${user.name}'s avatar">
                <span class="user-name">${user.name}</span>
                ${user.online ? '<span class="online-indicator"></span>' : ""}
            `;

      userItem.addEventListener("click", () => {
        selectUser(user);
      });

      userList.appendChild(userItem);
    });
  }

  function selectUser(user) {
    selectedUser = user;

    // Update chat header
    chatAvatar.src = user.avatar;
    chatUsername.textContent = user.name;
    chatOnlineIndicator.classList.toggle("hidden", !user.online);

    // Request message history
    socket.emit("get_messages", {
      recipient_id: user.id,
    });

    // Show chat view
    userListView.classList.add("hidden");
    chatView.classList.remove("hidden");
  }

  function showUserList() {
    selectedUser = null;
    messageList.innerHTML = "";
    userListView.classList.remove("hidden");
    chatView.classList.add("hidden");
  }

  function renderMessages(messages) {
    // Clear current messages
    messageList.innerHTML = "";

    // Add each message
    messages.forEach((message) => {
      const isCurrentUser = message.sender === currentUser.id;
      const messageItem = document.createElement("li");
      messageItem.className = isCurrentUser
        ? "message-item message-sent"
        : "message-item message-received";

      // Format timestamp
      const timestamp = new Date(message.timestamp);
      const formattedTime = timestamp.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });

      messageItem.innerHTML = `
                <p class="message-text">${message.text}</p>
                <div class="message-timestamp">${formattedTime}</div>
            `;

      messageList.appendChild(messageItem);
    });

    // Scroll to bottom
    messageList.scrollTop = messageList.scrollHeight;
  }

  function sendMessage() {
    const text = messageInput.value.trim();
    if (text && selectedUser) {
      socket.emit("send_message", {
        recipient_id: selectedUser.id,
        text: text,
      });

      // Clear input
      messageInput.value = "";
    }
  }

  function isCorrectRoom(room_id) {
    if (!selectedUser) return false;

    const user_ids = [currentUser.id, selectedUser.id].sort();
    const expected_room_id = `${user_ids[0]}_${user_ids[1]}`;

    return room_id === expected_room_id;
  }
});
