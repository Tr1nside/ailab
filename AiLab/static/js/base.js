const nightModeButton = document.querySelector('.night-mode');

// Функция для обновления иконки
function updateNightModeIcon() {
    const isDark = document.body.classList.contains('dark-mode');
    nightModeButton.innerHTML = isDark 
        ? '<img src="../static/img/icons/sun.svg" alt="sun" class="icon-header">' 
        : '<img src="../static/img/icons/moon.svg" alt="moon" class="icon-header">';
}

// Переключение между режимами
let darkMode = false;
if (!localStorage.getItem("darkMod")) {
    localStorage.setItem("darkMod", false);
    darkMode = false;
} else {
    darkMode = localStorage.getItem("darkMod");
    if (darkMode) {
        document.body.classList.toggle('dark-mode');
        updateNightModeIcon();
    }
}

const storedTheme = localStorage.getItem('theme');
if (storedTheme === 'dark') {
    document.body.classList.add('dark-mode');
} else {
    document.body.classList.remove('dark-mode');
}
updateNightModeIcon();

nightModeButton.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateNightModeIcon();
});

if (typeof socketio !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        socketio.emit('join_user_room');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Устанавливаем курсор для всех изображений с атрибутом data-enlargeable
    document.querySelectorAll('img[data-enlargeable]').forEach(img => {
        img.style.cursor = 'zoom-in';
    });

    // Обработчик кликов на body с делегированием событий
    document.body.addEventListener('click', function(e) {
        if (e.target.matches('img[data-enlargeable]')) {
            const src = e.target.src;
            const modal = document.createElement('div');
            
            // Стили модального окна
            modal.style.cssText = `
                background: rgba(0, 0, 0, 0.9) url(${src}) no-repeat center;
                background-size: contain;
                width: 100%;
                height: 100%;
                position: fixed;
                top: 0;
                left: 0;
                z-index: 10000;
                cursor: zoom-out;
            `;
            
            // Функция для закрытия модального окна
            function closeModal() {
                document.body.removeChild(modal);
                document.removeEventListener('keyup', closeOnEscape);
            }
            
            // Закрытие при клике на модальное окно
            modal.addEventListener('click', closeModal);
            
            // Закрытие по Escape
            function closeOnEscape(e) {
                if (e.key === 'Escape') {
                    closeModal();
                }
            }
            
            document.addEventListener('keyup', closeOnEscape);
            document.body.appendChild(modal);
        }
    });
});