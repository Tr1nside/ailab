const editButton = document.getElementById("edit-profile-btn");
const cancelButton = document.getElementById("cancel-button");
const modal = document.getElementById("edit-modal");

const state = {
  isModalOpen: false,
  toggleModal() {
    this.isModalOpen = !this.isModalOpen;
    updateUI();
  }
};

editButton.addEventListener("click", () => {
  state.toggleModal();
});

cancelButton.addEventListener("click", () => {
  state.isModalOpen = false;
  updateUI();
  modal.classList.add("hidden");
});

function updateUI() {
  if (state.isModalOpen) {
    modal.classList.remove("hidden");
  } else {
    modal.classList.add("hidden");
  }
}

modal.addEventListener("click", (e) => {
  if (e.target === modal) {
    state.toggleModal();
  }
});

document.querySelector(".modal-content").addEventListener("click", (e) => {
  e.stopPropagation();
});

document.getElementById("profile-form").addEventListener("submit", () => {
  setTimeout(() => {
      location.reload();  // Перезагрузка страницы после сохранения
  }, 500);
});

document.getElementById('profile-form').addEventListener('submit', function(e) {
  const form = e.target;
  if (!form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
  }
  form.classList.add('was-validated');
});