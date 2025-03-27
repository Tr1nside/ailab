const telegramInput = document.querySelector('.telegram-input');

telegramInput.addEventListener('input', function() {
  this.style.height = 'auto'; // Сброс высоты
  this.style.height = Math.min(this.scrollHeight, 150) + 'px'; // Ограничение по max-height
});