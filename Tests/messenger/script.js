document.addEventListener("DOMContentLoaded", () => {
    // State management
    const state = {
      isMessengerOpen: false,
      activeChat: null,
      messageText: "",
      showEmojiPicker: false,
      searchText: "",
      filteredContacts() {
        if (!this.searchText) return this.contacts;
        return this.contacts.filter((contact) =>
          contact.name.toLowerCase().includes(this.searchText.toLowerCase()),
        );
      },
      emojis: [
        "😊",
        "😂",
        "❤️",
        "👍",
        "😍",
        "🎉",
        "😎",
        "🤔",
        "😢",
        "😡",
        "🥰",
        "😴",
        "🤗",
        "😇",
        "🤩",
        "😋",
        "😉",
        "🙄",
        "😌",
        "🤓",
      ],
      messages: {},
      contacts: [
        {
          id: 1,
          name: "Иссус",
          status: "online",
          avatar: null,
        },
        {
          id: 2,
          name: "Vlad Is Slave",
          status: "offline",
          avatar: null,
        },
      ],
      toggleMessenger() {
        this.isMessengerOpen = !this.isMessengerOpen;
        updateUI();
      },
      openChat(contactId) {
        this.activeChat = this.contacts.find(
          (contact) => contact.id === contactId,
        );
        updateUI();
      },
      closeChat() {
        this.activeChat = null;
        updateUI();
      },
      insertEmoji(emoji) {
        this.messageText += emoji;
        this.showEmojiPicker = false;
        updateUI();
      },
      sendMessage() {
        if (this.messageText.trim()) {
          const chatId = this.activeChat.id;
          if (!this.messages[chatId]) {
            this.messages[chatId] = [];
          }
          this.messages[chatId].push({
            text: this.messageText,
            timestamp: new Date().toISOString(),
          });
          this.messageText = "";
          updateUI();
        }
      },
    };
  
    // DOM Elements
    const chatMessenger = document.getElementById("chatMessenger");
    const toggleButton = document.getElementById("toggleButton");
    const contactsListContainer = document.createElement("div");
    contactsListContainer.className = "contacts-list-container";
    const chatViewContainer = document.createElement("div");
    chatViewContainer.className = "chat-view-container";
  
    // Templates
    const contactsListTemplate = document.getElementById("contactsListTemplate");
    const contactItemTemplate = document.getElementById("contactItemTemplate");
    const chatViewTemplate = document.getElementById("chatViewTemplate");
    const emojiPickerTemplate = document.getElementById("emojiPickerTemplate");
    const emojiItemTemplate = document.getElementById("emojiItemTemplate");
  
    // Event Listeners
    toggleButton.addEventListener("click", () => {
      state.toggleMessenger();
    });
  
    // UI Update Function
    function updateUI() {
      // Update messenger visibility
      chatMessenger.style.display = state.isMessengerOpen ? "flex" : "none";
      chatMessenger.style.transform = state.isMessengerOpen
        ? "translateX(0)"
        : "translateX(100%)";
  
      // Clear containers
      contactsListContainer.innerHTML = "";
      chatViewContainer.innerHTML = "";
  
      // Render appropriate view based on state
      if (!state.activeChat) {
        renderContactsList();
      } else {
        renderChatView();
      }
    }
  
    // Render Contacts List
    function renderContactsList() {
      // Clone contacts list template
      const contactsListClone = contactsListTemplate.content.cloneNode(true);
      contactsListContainer.appendChild(contactsListClone);
  
      // Set up search input
      const searchInput = contactsListContainer.querySelector("#searchInput");
      searchInput.value = state.searchText;
      searchInput.addEventListener("input", (e) => {
        state.searchText = e.target.value;
        updateUI();
      });
  
      // Render contacts
      const contacts = state.filteredContacts();
      contacts.forEach((contact) => {
        const contactItemClone = contactItemTemplate.content.cloneNode(true);
        const contactItem = contactItemClone.querySelector(".contact-item");
  
        // Set contact name
        const contactName = contactItem.querySelector(".contact-name");
        contactName.textContent = contact.name;
  
        // Add click event
        contactItem.addEventListener("click", () => {
          state.openChat(contact.id);
        });
  
        contactsListContainer.appendChild(contactItemClone);
      });
  
      // Append to messenger
      chatMessenger
        .querySelector(".messenger-content")
        .appendChild(contactsListContainer);
    }
  
    // Render Chat View
    function renderChatView() {
      // Clone chat view template
      const chatViewClone = chatViewTemplate.content.cloneNode(true);
      chatViewContainer.appendChild(chatViewClone);
  
      // Set up back button
      const backButton = chatViewContainer.querySelector("#backButton");
      backButton.addEventListener("click", () => {
        state.closeChat();
      });
  
      // Set contact name in header and message
      const chatContactName =
        chatViewContainer.querySelector(".chat-contact-name");
      const chatContactNameDisplay = chatViewContainer.querySelector(
        ".chat-contact-name-display",
      );
      chatContactName.textContent = state.activeChat.name;
      chatContactNameDisplay.textContent = state.activeChat.name;
  
      // Set up emoji button
      const emojiButton = chatViewContainer.querySelector("#emojiButton");
      emojiButton.addEventListener("click", (e) => {
        e.stopPropagation();
        state.showEmojiPicker = !state.showEmojiPicker;
        updateUI();
      });
  
      // Render emoji picker if needed
      if (state.showEmojiPicker) {
        const emojiPickerClone = emojiPickerTemplate.content.cloneNode(true);
        const emojiPicker = emojiPickerClone.querySelector(".emoji-picker");
  
        // Add emojis
        state.emojis.forEach((emoji) => {
          const emojiItemClone = emojiItemTemplate.content.cloneNode(true);
          const emojiItem = emojiItemClone.querySelector(".emoji-item");
          emojiItem.textContent = emoji;
  
          emojiItem.addEventListener("click", () => {
            state.insertEmoji(emoji);
          });
  
          emojiPicker.appendChild(emojiItemClone);
        });
  
        chatViewContainer
          .querySelector(".emoji-container")
          .appendChild(emojiPickerClone);
      }
  
      // Set up message input
      const messageInput = chatViewContainer.querySelector("#messageInput");
      messageInput.value = state.messageText;
      messageInput.addEventListener("input", (e) => {
        state.messageText = e.target.value;
      });
      messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          state.sendMessage();
        }
      });
  
      // Set up send button
      const sendButton = chatViewContainer.querySelector("#sendButton");
      sendButton.addEventListener("click", () => {
        state.sendMessage();
      });
  
      // Append to messenger
      chatMessenger
        .querySelector(".messenger-content")
        .appendChild(chatViewContainer);
    }
  
    // Initialize UI
    updateUI();
  
    // Close emoji picker when clicking outside
    document.addEventListener("click", (e) => {
      if (state.showEmojiPicker && !e.target.closest(".emoji-container")) {
        state.showEmojiPicker = false;
        updateUI();
      }
    });
  });
  