document.addEventListener("DOMContentLoaded", () => {
    // State management
    const state = {
      isModalOpen: false,
      name: "Христос Исус Божьекоро��ков",
      email: "hesus@hristos.com",
      phone: "+7 535 353 53 53",
      position: "Админ",
      mediaUrl:
        "https://cdn.builder.io/api/v1/image/assets/TEMP/e2da710043e4586c96081718d0a1e7b92cb69ed0",
      mediaType: "image", // "image", "video", or "gif"
      socialMedia: {
        telegram: {
          id: "pipisya",
          url: "https://t.me/pipisya",
        },
        github: {
          id: "hesus",
          url: "https://github.com/hesus",
        },
        vk: {
          id: "hesus1",
          url: "https://vk.com/hesus1",
        },
      },
  
      // Methods to update state
      toggleModal() {
        this.isModalOpen = !this.isModalOpen;
        updateUI();
      },
  
      updateProfile(name, email, phone, position, mediaUrl, mediaType) {
        this.name = name;
        this.email = email;
        this.phone = phone;
        this.position = position;
        if (mediaUrl) {
          this.mediaUrl = mediaUrl;
          this.mediaType = mediaType || "image";
        }
        updateUI();
      },
  
      updateSocialMedia(platform, url) {
        let id = "";
  
        // Extract ID from URL if not empty
        if (url && url.trim() !== "") {
          id = url.split("/").pop() || "";
        }
  
        this.socialMedia[platform] = {
          id,
          url,
        };
  
        updateUI();
      },
  
      saveProfile(formData) {
        // Update all profile data at once
        // In a real app, this would likely send data to a server
  
        // Update profile information
        this.updateProfile(
          formData.name,
          formData.email,
          formData.phone,
          formData.position,
          formData.mediaUrl,
          formData.mediaType,
        );
  
        // Update social media
        this.updateSocialMedia("telegram", formData.telegram);
        this.updateSocialMedia("github", formData.github);
        this.updateSocialMedia("vk", formData.vk);
  
        // Close modal after saving
        this.toggleModal();
      },
    };
  
    // DOM Elements
    const editButton = document.getElementById("edit-profile-btn");
    const cancelButton = document.getElementById("cancel-button");
    const modal = document.getElementById("edit-modal");
    const profileForm = document.getElementById("profile-form");
    const photoUpload = document.getElementById("photo-upload");
    const currentPhotoPreview = document.getElementById("current-photo");
    const currentVideoPreview = document.getElementById("current-video");
    const profileImage = document.getElementById("profile-image");
    const profileVideo = document.getElementById("profile-video");
  
    // Variables to store the selected media
    let selectedMediaFile = null;
    let selectedMediaUrl = null;
    let selectedMediaType = null;
  
    // Event Listeners
    editButton.addEventListener("click", () => {
      state.toggleModal();
    });
    
    cancelButton.addEventListener("click", () => {
      // Сбрасываем состояние модального окна
      state.isModalOpen = false;
      
      // Сбрасываем выбранные медиа
      selectedMediaFile = null;
      selectedMediaUrl = null;
      selectedMediaType = null;
      
      // Обновляем UI
      updateUI();
      
      // Принудительно скрываем модальное окно
      modal.classList.add("hidden");
    });
  
    // Media upload handler
    photoUpload.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
  
      selectedMediaFile = file;
  
      // Determine media type
      if (file.type.match("video.*")) {
        selectedMediaType = "video";
      } else if (
        file.type === "image/gif" ||
        file.name.toLowerCase().endsWith(".gif")
      ) {
        selectedMediaType = "gif";
      } else if (file.type.match("image.*")) {
        selectedMediaType = "image";
      } else {
        alert("П��жалуйста, выберите изображение, GIF или видео");
        return;
      }
  
      // Create a preview of the selected media
      const reader = new FileReader();
      reader.onload = (event) => {
        selectedMediaUrl = event.target.result;
  
        // Update preview based on media type
        if (selectedMediaType === "video") {
          // Show video preview, hide image preview
          currentPhotoPreview.classList.add("hidden");
          currentVideoPreview.classList.remove("hidden");
  
          // Set video source
          currentVideoPreview.src = selectedMediaUrl;
          currentVideoPreview.load();
        } else {
          // Show image preview, hide video preview
          currentPhotoPreview.classList.remove("hidden");
          currentVideoPreview.classList.add("hidden");
  
          // Set image source
          currentPhotoPreview.src = selectedMediaUrl;
        }
      };
      reader.readAsDataURL(file);
    });
  
    profileForm.addEventListener("submit", (e) => {
      e.preventDefault();
  
      const formData = {
        name: document.getElementById("input-name").value,
        email: document.getElementById("input-email").value,
        phone: document.getElementById("input-phone").value,
        position: document.getElementById("input-position").value,
        mediaUrl: selectedMediaUrl,
        mediaType: selectedMediaType,
        telegram: document.getElementById("input-telegram").value.trim(),
        github: document.getElementById("input-github").value.trim(),
        vk: document.getElementById("input-vk").value.trim(),
      };
  
      // Clear empty social media fields
      if (!formData.telegram) {
        state.socialMedia.telegram = { id: "", url: "" };
      }
  
      if (!formData.github) {
        state.socialMedia.github = { id: "", url: "" };
      }
  
      if (!formData.vk) {
        state.socialMedia.vk = { id: "", url: "" };
      }
  
      state.saveProfile(formData);
    });
  
    // Update UI based on state
    function updateUI() {
      // Update modal visibility
      if (state.isModalOpen) {
        modal.classList.remove("hidden");
      } else {
        modal.classList.add("hidden");
      }
  
      // Update profile information displays
      document.querySelector(".profile-name").textContent = state.name;
      document.querySelector(".profile-email").textContent = state.email;
      document.querySelector(".profile-phone").textContent = state.phone;
      document.getElementById("user-position").textContent = state.position;
  
      // Update profile media based on type
      if (state.mediaType === "video") {
        // Show video, hide image
        profileImage.classList.add("hidden");
        profileVideo.classList.remove("hidden");
  
        // Set video source if it's different
        if (profileVideo.src !== state.mediaUrl) {
          profileVideo.src = state.mediaUrl;
          profileVideo.load();
        }
      } else {
        // Show image, hide video
        profileImage.classList.remove("hidden");
        profileVideo.classList.add("hidden");
  
        // Set image source
        profileImage.src = state.mediaUrl;
      }
  
      // Update media preview in modal if not already set by user
      if (!selectedMediaUrl) {
        if (state.mediaType === "video") {
          currentPhotoPreview.classList.add("hidden");
          currentVideoPreview.classList.remove("hidden");
          currentVideoPreview.src = state.mediaUrl;
          currentVideoPreview.load();
        } else {
          currentPhotoPreview.classList.remove("hidden");
          currentVideoPreview.classList.add("hidden");
          currentPhotoPreview.src = state.mediaUrl;
        }
      }
  
      // Update social media displays
      // Telegram
      const telegramContainer = document.getElementById("telegram-container");
      const telegramId = state.socialMedia.telegram.id;
      if (telegramId && telegramId.trim() !== "") {
        telegramContainer.classList.remove("hidden");
        document.getElementById("telegram-id").textContent = telegramId;
      } else {
        telegramContainer.classList.add("hidden");
      }
  
      // GitHub
      const githubContainer = document.getElementById("github-container");
      const githubId = state.socialMedia.github.id;
      if (githubId && githubId.trim() !== "") {
        githubContainer.classList.remove("hidden");
        document.getElementById("github-id").textContent = githubId;
      } else {
        githubContainer.classList.add("hidden");
      }
  
      // VK
      const vkContainer = document.getElementById("vk-container");
      const vkId = state.socialMedia.vk.id;
      if (vkId && vkId.trim() !== "") {
        vkContainer.classList.remove("hidden");
        document.getElementById("vk-id").textContent = vkId;
      } else {
        vkContainer.classList.add("hidden");
      }
      // Update form values when modal opens
      document.getElementById("input-name").value = state.name;
      document.getElementById("input-email").value = state.email;
      document.getElementById("input-phone").value = state.phone;
      document.getElementById("input-position").value = state.position;
      document.getElementById("input-telegram").value =
        state.socialMedia.telegram.url;
      document.getElementById("input-github").value =
        state.socialMedia.github.url;
      document.getElementById("input-vk").value = state.socialMedia.vk.url;
    }

  
    // Initialize UI
    updateUI();
  
    // Close modal when clicking outside
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        state.toggleModal();
      }
    });
  
    // Prevent event propagation from modal content
    document.querySelector(".modal-content").addEventListener("click", (e) => {
      e.stopPropagation();
    });
  });
  



