const nightModeButton = document.querySelector('.night-mode');
const contextMenu = document.getElementById('contextMenu');
const contextMenuList = document.getElementById('contextMenuList');
let currentContextType = null;
let currentContextElement = null; // Добавляем переменную для хранения элемента


function attachAttachmentListeners() {
    const docElements = document.querySelectorAll('.message-doc.context-area');
    docElements.forEach(doc => {
        doc.addEventListener('click', function (e) {
            e.preventDefault();
            const fileUrl = doc.getAttribute('href');
            const fileName = doc.textContent.trim();
            const extension = fileName.split('.').pop().toLowerCase();
            const codeExtensions = ['py', 'cpp', 'js', 'html'];

            // Проверяем, является ли файл кодовым и находится ли пользователь на /ide
            if (codeExtensions.includes(extension) && isIdePage()) {
                // Загружаем содержимое файла через fetch
                fetch(fileUrl)
                    .then(response => {
                        if (!response.ok) throw new Error('Не удалось загрузить файл');
                        return response.text(); // Получаем содержимое как текст
                    })
                    .then(content => {
                        // Вызываем функцию создания новой вкладки
                        window.createNewTabWithContent(fileName, content);
                    })
                    .catch(error => {
                        console.error('Ошибка загрузки файла:', error);
                        alert('Не удалось открыть файл в редакторе');
                    });
            } else {
                // Для некодовых файлов или если не на /ide — стандартное скачивание
                const link = document.createElement('a');
                link.href = fileUrl;
                link.download = fileName;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        });
    });
}

// Обработчик правого клика
document.addEventListener('contextmenu', (e) => {
    e.preventDefault();

    const contextArea = e.target.closest('.context-area');
    if (!contextArea) return;

    currentContextType = contextArea.dataset.contextType;
    currentContextElement = contextArea; // Сохраняем элемент
    loadContextMenu(currentContextType, e.clientX, e.clientY);
});

// Закрытие меню при клике вне его
document.addEventListener('click', () => {
    contextMenu.style.display = 'none';
});

// Загрузка меню с сервера
async function loadContextMenu(contextType, x, y) {
    try {
        const response = await fetch(`/api/context-menu?type=${contextType}`);
        const data = await response.json();
        renderContextMenu(data.items, x, y);
    } catch (error) {
        console.error('Ошибка загрузки меню:', error);
    }
}

// Отрисовка пунктов меню
function renderContextMenu(items, x, y) {
    contextMenuList.innerHTML = '';

    items.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item.label;
        li.addEventListener('click', () => handleMenuAction(item.action));
        contextMenuList.appendChild(li);
    });

    contextMenu.style.left = `${x}px`;
    contextMenu.style.top = `${y}px`;
    contextMenu.style.display = 'block';
}

// Обработка выбора пункта меню
function handleMenuAction(action) {
    if (!currentContextElement) return; // Проверяем, что элемент сохранён

    if (action === "edit") {
        const messageElement = currentContextElement.closest('.message');
        const messageTextElement = messageElement.querySelector('.message-text');
        const messageId = currentContextElement.dataset.id;
        const originalText = messageTextElement.innerText;

        // Создаём поле ввода
        const input = document.createElement('textarea');
        input.value = originalText;
        input.classList.add('edit-message-input');
        input.style.width = '100%';
        input.style.minHeight = '40px';

        // Заменяем текст на поле ввода
        messageTextElement.innerHTML = '';
        messageTextElement.appendChild(input);
        input.focus();

        // Обработчик сохранения
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const newText = input.value.trim();
                if (newText && newText !== originalText) {
                    const postData = {
                        action: 'edit',
                        element: {
                            id: messageId,
                            type: currentContextType,
                            content: newText
                        }
                    };

                    fetch('/api/execute-action', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrf_token')
                        },
                        body: JSON.stringify(postData)
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === "success") {
                                messageTextElement.innerText = newText;
                                const recipientId = data.recipient_id;
                                if (recipientId) loadChat(recipientId); // Обновляем чат
                            } else {
                                alert("Ошибка: " + data.message);
                                messageTextElement.innerText = originalText; // Восстанавливаем текст
                            }
                        })
                        .catch(error => {
                            console.error("Ошибка:", error);
                            alert("Не удалось сохранить изменения");
                            messageTextElement.innerText = originalText;
                        });
                } else {
                    messageTextElement.innerText = originalText; // Восстанавливаем текст
                }
            }
            if (e.key === 'Escape') {
                messageTextElement.innerText = originalText; // Отмена
            }
        });

        contextMenu.style.display = 'none';
        return;
    } else if (action === "download") {
        // Получаем элемент, на котором вызвали меню (это точно <img> или <video>)
        const mediaElement = currentContextElement;
        
        // Определяем URL и имя файла
        let fileUrl;
        let fileName;
        
        if (mediaElement.tagName === 'IMG') {
            fileUrl = mediaElement.src;
            fileName = mediaElement.alt || `image_${Date.now()}.jpg`;
        } 
        else if (mediaElement.tagName === 'VIDEO') {
            // Для video берём источник или poster
            fileUrl = mediaElement.querySelector('source')?.src || 
                     mediaElement.poster || 
                     mediaElement.src;
            fileName = mediaElement.dataset.filename || `video_${Date.now()}.mp4`;
        } else {    
            fileUrl = mediaElement.href;
            fileName = mediaElement.alt || `image_${Date.now()}.jpg`;
        }
    
        if (!fileUrl) {
            console.error('URL файла не найден');
            return;
        }
    
        // Создаём скрытую ссылку для скачивания
        const link = document.createElement('a');
        link.href = fileUrl;
        link.download = fileName;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    
        // Закрываем контекстное меню
        contextMenu.style.display = 'none';
    }
    

    // Логика для других действий (delete, clear_history)
    const postData = {
        action: action,
        element: {
            id: currentContextElement.dataset.id,
            type: currentContextType,
            content: currentContextElement.innerText
        }
    };

    fetch('/api/execute-action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrf_token')
        },
        body: JSON.stringify(postData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                if (action === "delete") {
                    currentContextElement.closest('.message').remove();
                } else if (action === "clear_history") {
                    const recipientId = data.recipient_id;
                    if (recipientId) loadChat(recipientId);
                }
            } else {
                alert("Ошибка: " + data.message);
            }
        })
        .catch(error => {
            console.error("Ошибка:", error);
            alert("Не удалось выполнить действие");
        });

    contextMenu.style.display = 'none';
}


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