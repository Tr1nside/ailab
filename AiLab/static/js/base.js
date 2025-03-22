const nightModeButton = document.querySelector('.night-mode');

// Переключение между режимами
let darkMode = false;
if (!localStorage.getItem("darkMod")) {
    localStorage.setItem("darkMod", false);
    darkMode = false;
} else {
    darkMode = localStorage.getItem("darkMod");
    if (darkMode) {
        document.body.classList.toggle('dark-mode');
        nightModeButton.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
    }
}

const storedTheme = localStorage.getItem('theme');
if (storedTheme === 'dark') {
    document.body.classList.add('dark-mode');
    nightModeButton.textContent = '☀️';
} else {
    document.body.classList.remove('dark-mode');
    nightModeButton.textContent = '🌙';
}

nightModeButton.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    nightModeButton.textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
});
