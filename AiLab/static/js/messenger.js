const header = document.querySelector('.header');
if (header) {
    document.documentElement.style.setProperty(
        '--header-height', 
        `${header.offsetHeight}px`
    );
}

// Инициализация Socket.IO с правильными параметрами
const socketio = io({
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    transports: ['websocket', 'polling'], // Явно указываем транспорты
    withCredentials: true
});

// Функция для фильтрации контактов
function filterContacts(searchTerm) {
    const contacts = document.querySelectorAll('.contact-item');
    searchTerm = searchTerm.toLowerCase();
    
    contacts.forEach(contact => {
        const name = contact.querySelector('.contact-name').textContent.toLowerCase();
        if (name.includes(searchTerm)) {
            contact.style.display = 'flex';
        } else {
            contact.style.display = 'none';
        }
    });
}

// Функция обновления статуса пользователя
function updateUserStatus(userId, isOnline) {
    const statusElement = document.querySelector(`.status-indicator[data-user-id="${userId}"]`);
    if (statusElement) {
        statusElement.classList.toggle('online', isOnline);
        statusElement.classList.toggle('offline', !isOnline);
    }
}

// Функция для быстрого обновления счетчика
function updateMessageCounter(increment = 1) {
    const badge = document.getElementById('unread-count');
    if (badge) {
        const currentCount = parseInt(badge.textContent) || 0;
        badge.textContent = currentCount + increment;
        badge.classList.toggle('hidden', currentCount + increment <= 0);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const messengerButton = document.querySelector('.messenger-icon');
    const messengerContainer = document.getElementById('messenger-container');
    const closeMessenger = document.getElementById('close-messenger');
    const messengerContent = document.getElementById('messenger-content');
    const searchInput = document.getElementById('contact-search');

    // Обработчик поиска
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterContacts(this.value);
        });
    }

    // Открытие/закрытие мессенджера
    messengerButton.addEventListener('click', function() {
        messengerContainer.classList.toggle('open');
        if (messengerContainer.classList.contains('open')) {
            loadContacts();
        }
    });
    
    closeMessenger.addEventListener('click', function() {
        messengerContainer.classList.remove('open');
        if (searchInput) searchInput.value = '';
        filterContacts('');
    });

    // Загрузка списка контактов
    function loadContacts() {
        document.getElementById('messenger-header').classList.remove('hidden');
        fetch('/messenger/contacts')
            .then(response => response.text())
            .then(html => {
                document.getElementById('messenger-content').innerHTML = html;
                attachContactListeners();
                scrollToBottom();
            });
    }
    
    // Обработчики для контактов
    function attachContactListeners() {
        const contactItems = document.querySelectorAll('.contact-item');
        contactItems.forEach(item => {
            item.addEventListener('click', function() {
                const userId = this.dataset.userId;
                loadChat(userId);
            });
        });
    }
    
    function formatMessageTimes() {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const yesterday = today - 86400000; // 24 часа в миллисекундах
    
        document.querySelectorAll('.message-time').forEach(element => {
            const isoString = element.dataset.timestamp;
            if (!isoString) return;
    
            // Создаём дату в UTC
            const messageDateUTC = new Date(isoString);
            if (isNaN(messageDateUTC.getTime())) return;
    
            // Корректируем на часовой пояс пользователя
            const userOffset = new Date().getTimezoneOffset() * 60000; // В миллисекундах
            const messageDate = new Date(messageDateUTC.getTime() - userOffset); // Переводим в локальное время
    
            // Определяем локаль пользователя
            const locale = navigator.language || 'ru-RU';
    
            // Получаем локализованное время
            const timeStr = messageDate.toLocaleTimeString(locale, {
                hour: '2-digit',
                minute: '2-digit'
            });
    
            // Определяем начало дня для сообщения
            const messageDayStart = new Date(
                messageDate.getFullYear(),
                messageDate.getMonth(),
                messageDate.getDate()
            ).getTime();

            if (messageDayStart === today) {
                element.textContent = timeStr;
            } else if (messageDayStart === yesterday) {
                element.textContent = `вчера в ${timeStr}`;
            } else {
                const dateStr = messageDate.toLocaleDateString(locale, {
                    day: '2-digit',
                    month: '2-digit',
                    year: messageDate.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
                });
    
                element.textContent = `${dateStr} ${timeStr}`;
            }
        });
    }
    

    // Загрузка чата с пользователем
    function loadChat(userId) {
        document.getElementById('messenger-header').classList.add('hidden');
        fetch(`/messenger/chat/${userId}`)
            .then(response => response.text())
            .then(html => {
                document.getElementById('messenger-content').innerHTML = html;
                formatMessageTimes(); // Вызов функции форматирования
                
                // Пометить сообщения как прочитанные
                fetch(`/messenger/mark_as_read/${userId}`, { 
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrf_token') }
                }).then(() => checkNewMessages());
                
                attachChatListeners(userId);
                scrollToBottom();
            });
    }
    
    function attachChatListeners(userId) {
        const input = document.getElementById('message-input');
        const sendButton = document.querySelector('.send-button');
        const messagesContainer = document.getElementById('messages-container');
    
        function sendMessage() {
            const text = input.value.trim();
            if (text) {
                fetch('/messenger/send', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrf_token')
                    },
                    body: JSON.stringify({
                        recipient_id: userId,
                        text: text
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        input.value = '';
                        loadChat(userId);
                    }
                });
            }
        }
    
        sendButton.addEventListener('click', sendMessage);
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        input.focus();
        
        const backButton = document.querySelector('.back-button');
        if (backButton) {
            backButton.addEventListener('click', loadContacts);
        }
    }
    
    function scrollToBottom() {
        const container = document.getElementById('messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
    
    // Получение CSRF токена
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }
    
    // Проверка новых сообщений
    function checkNewMessages() {
        fetch('/messenger/check_new')
            .then(response => response.json())
            .then(data => {
                const badge = document.getElementById('unread-count');
                if (badge) {
                    badge.textContent = data.count;
                    badge.classList.toggle('hidden', data.count <= 0);
                }
            });
    }
    
    // Настройка обработчиков Socket.IO
    function setupSocketListeners() {
        socketio.on('connect', function() {
            console.log('Socket.IO connected');
            socketio.emit('join_user_room');
        });

        socketio.on('new_message', function(data) {
            formatMessageTimes();
            // Быстрое обновление счетчика
            const badge = document.getElementById('unread-count');
            if (badge) {
                const currentCount = parseInt(badge.textContent) || 0;
                badge.textContent = currentCount + 1;
                badge.classList.remove('hidden');
            }

            playNotificationSound()

            // Обновляем чат если он открыт
            const currentChat = document.querySelector('.chat-header');
            if (currentChat && currentChat.dataset.userId == data.sender_id) {
                loadChat(data.sender_id);
            }
        });

        socketio.on('user_online', function(data) {
            console.log('User status:', data.user_id, data.online ? 'online' : 'offline');
            const statusElement = document.querySelector(`.status-indicator[data-user-id="${data.user_id}"]`);
            if (statusElement) {
                statusElement.classList.toggle('online', data.online);
                statusElement.classList.toggle('offline', !data.online);
            }
        });

        socketio.on('connect_error', function(err) {
            console.error('Socket.IO connection error:', err);
        });
    }

    // Инициализация
    setupSocketListeners();
    checkNewMessages();
    setInterval(checkNewMessages, 30000);
});