const nightModeButton = document.querySelector('.night-mode');

// Функция для обновления иконки
function updateNightModeIcon() {
    const isDark = document.body.classList.contains('dark-mode');
    nightModeButton.innerHTML = isDark 
        ? '<img src="../static/img/icons/sun.svg" alt="sun">' 
        : '<img src="../static/img/icons/moon.svg" alt="moon">';
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