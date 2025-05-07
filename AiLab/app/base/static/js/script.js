const body = document.body;
const tabs = document.querySelector('.tabs');
let codeMirrorInstances = {};
const consoleOutput = document.querySelector('.console-output');
const consoleInput = document.querySelector('.console-input');
const socket = io();
const languageSelect = document.querySelector('#language-select');

// 🔹 Список ключевых слов и встроенных функций Python для автодополнения
const pythonKeywords = [
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
    "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "callable",
    "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir",
    "divmod", "enumerate", "eval", "exec", "filter", "float", "format",
    "frozenset", "getattr", "globals", "hasattr", "hash", "help", "hex",
    "id", "input", "int", "isinstance", "issubclass", "iter", "len",
    "list", "locals", "map", "max", "memoryview", "min", "next", "object",
    "oct", "open", "ord", "pow", "print", "property", "range", "repr",
    "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod",
    "str", "sum", "super", "tuple", "type", "vars", "zip",
    "list", "tuple", "set", "frozenset", "dict",
    "deque", "defaultdict", "OrderedDict", "Counter", "ChainMap", "namedtuple",
    "dataclass",
    "array", "heapq", "queue", "PriorityQueue",
    "self", "__init__", "__main__", "os", "sys", "json", "time", "re",
    "math", "random", "datetime", "open", "read", "write", "close"
];

let saveInterval = null;

function manageAutoSave(tabId, filePath) {
    if (saveInterval) {
        clearInterval(saveInterval);
    }
    if (filePath && codeMirrorInstances[tabId]) {
        let lastContent = codeMirrorInstances[tabId].getValue();
        saveInterval = setInterval(() => {
            const currentContent = codeMirrorInstances[tabId].getValue();
            if (currentContent !== lastContent) {
                saveContentToFile(filePath, currentContent);
                lastContent = currentContent;
            }
        }, 7000);
    }
}

// 🔹 Функция для автодополнения
function pythonHint(cm) {
    const cur = cm.getCursor();
    const token = cm.getTokenAt(cur);
    const start = token.start;
    const end = cur.ch;
    const word = token.string.slice(0, end - start);
    if (!word.length) return;

    const existingWords = new Set(pythonKeywords);
    const doc = cm.getValue().match(/\b\w+\b/g) || [];
    doc.forEach(w => existingWords.add(w));

    const list = [...existingWords].filter(item => item.startsWith(word));

    return {
        list: list,
        from: CodeMirror.Pos(cur.line, start),
        to: CodeMirror.Pos(cur.line, end)
    };
}

// 🔹 Функция инициализации CodeMirror
function initializeCodeMirror(codeArea, content = "", filePath = null) {
    const cm = CodeMirror(codeArea, {
        mode: languageSelect.value === "python" ? "python" : "text/x-c++src",
        theme: body.classList.contains('dark-mode') ? "dracula" : "default",
        lineNumbers: true,
        gutters: ["CodeMirror-linenumbers"],
        autoCloseBrackets: true,
        indentWithTabs: false,
        tabSize: 4,
        smartIndent: true,
        electricChars: true,
        extraKeys: {
            "Ctrl-Space": function(cm) {
                cm.showHint({ hint: pythonHint, completeSingle: false });
            },
            "Tab": function(cm) {
                if (cm.somethingSelected()) {
                    cm.indentSelection("add");
                } else {
                    cm.replaceSelection("    ", "end", "+input");
                }
            },
            "Shift-Tab": function(cm) {
                cm.indentSelection("subtract");
            },
            "Ctrl-/": function(cm) {
                cm.execCommand("toggleComment");
            },
            "Ctrl-S": function(cm) {
                if (filePath) {
                    saveContentToFile(filePath, cm.getValue());
                }
            }
        }
    });
    cm.setValue(content);
    cm.on("inputRead", function(cm, change) {
        if (change.text[0].match(/\w/) && cm.getTokenAt(cm.getCursor()).string.length > 0) {
            setTimeout(() => cm.showHint({ hint: pythonHint, completeSingle: false }), 100);
        }
    });
    return cm;
}

// 🔹 Функция для сохранения содержимого в файл через API
function saveContentToFile(filePath, content) {
    const postData = {
        action: 'write_file',
        element: { path: filePath, content: content }
    };
    fetch('/api/file-action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrf_token')
        },
        body: JSON.stringify(postData)
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status !== 'success') {
                showNotification(`Ошибка сохранения: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Ошибка сохранения:', error);
            showNotification('Не удалось сохранить файл');
        });
}

// 🔹 Функция для загрузки содержимого файла через API
function loadFileContent(filePath) {
    return fetch('/api/file-action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrf_token')
        },
        body: JSON.stringify({
            action: 'read_file',
            element: { path: filePath }
        })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                return data.content;
            } else {
                throw new Error(`Ошибка загрузки: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Ошибка загрузки файла:', error);
            showNotification('Не удалось загрузить файл');
            return "";
        });
}

// 🔹 Получение CSRF-токена
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

consoleInput.addEventListener('focus', () => {
    if (consoleInput.readOnly) {
        consoleInput.blur();
    }
});

consoleInput.readOnly = true;

function updateConsoleInputClass() {
    if (consoleInput.readOnly) {
        consoleInput.classList.remove('console-input-active');
    } else {
        consoleInput.classList.add('console-input-active');
    }
}
updateConsoleInputClass();

// 🔹 Функция для поиска свободного ID вкладки
function getNextTabId() {
    const existingIds = new Set();
    document.querySelectorAll('.tab').forEach(tab => {
        const num = parseInt(tab.dataset.tab.replace("tab", ""), 10);
        existingIds.add(num);
    });
    let newId = 1;
    while (existingIds.has(newId)) {
        newId++;
    }
    return `tab${newId}`;
}

// 🔹 Функция создания новой вкладки
function createNewTab(customId = null, fileName = null, content = "", filePath = null, activate = true) {
    const newTabId = customId || getNextTabId();
    const newFileName = fileName || `file${newTabId.replace("tab", "")}.py`;

    const newTab = document.createElement('div');
    newTab.classList.add('tab');
    newTab.dataset.tab = newTabId;
    newTab.dataset.filePath = filePath || '';
    newTab.innerHTML = `<span>${newFileName}</span><span class="close-tab">×</span>`;
    tabs.appendChild(newTab);

    const codeArea = document.createElement('div');
    codeArea.classList.add('code-area');
    codeArea.dataset.tabContent = newTabId;
    document.querySelector('.container').insertBefore(codeArea, document.querySelector('.toolbar'));

    const cm = initializeCodeMirror(codeArea, content, filePath);
    codeMirrorInstances[newTabId] = cm;

    if (activate) activateTab(newTab);

    saveTabsToLocalStorage();
}

// 🔹 Экспортируемая функция для открытия вкладки с содержимым и путём
window.openFileInTab = function(filePath, content) {
    let existingTab = null;
    document.querySelectorAll('.tab').forEach(tab => {
        if (tab.dataset.filePath === filePath) {
            existingTab = tab;
        }
    });

    if (existingTab) {
        const tabId = existingTab.dataset.tab;
        codeMirrorInstances[tabId].setValue(content);
        activateTab(existingTab);
    } else {
        const fileName = filePath.split('/').pop();
        const newTabId = getNextTabId();
        createNewTab(newTabId, fileName, content, filePath, true);
    }
};

// 🔹 Функция для обновления вкладок при переименовании
window.updateTabsOnRename = function(oldPath, newPath) {
    document.querySelectorAll('.tab').forEach(tab => {
        const tabFilePath = tab.dataset.filePath;
        if (tabFilePath === oldPath || tabFilePath.startsWith(oldPath + '/')) {
            const updatedPath = tabFilePath === oldPath
                ? newPath
                : newPath + tabFilePath.substring(oldPath.length);
            tab.dataset.filePath = updatedPath;
            const newFileName = updatedPath.split('/').pop();
            tab.querySelector('span').textContent = newFileName;
            const tabId = tab.dataset.tab;
            manageAutoSave(tabId, updatedPath);
        }
    });
    saveTabsToLocalStorage();
};

// 🔹 Функция активации вкладки
function activateTab(tab) {
    const tabId = tab.dataset.tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.code-area[data-tab-content]').forEach(content => content.style.display = 'none');
    tab.classList.add('active');
    const codeArea = document.querySelector(`.code-area[data-tab-content="${tabId}"]`);
    codeArea.style.display = 'block';
    if (codeMirrorInstances[tabId]) {
        codeMirrorInstances[tabId].refresh();
    }
    manageAutoSave(tabId, tab.dataset.filePath);
}

// 🔹 Функция закрытия вкладки
function closeTab(tab) {
    const tabId = tab.dataset.tab;
    document.querySelector(`.tab[data-tab="${tabId}"]`).remove();
    document.querySelector(`.code-area[data-tab-content="${tabId}"]`).remove();
    delete codeMirrorInstances[tabId];
    const firstTab = document.querySelector('.tab');
    if (firstTab) {
        activateTab(firstTab);
    }
    saveTabsToLocalStorage();
}

// 🔹 Сохранение вкладок в localStorage
function saveTabsToLocalStorage() {
    const tabsData = [];
    document.querySelectorAll('.tab').forEach(tab => {
        const tabId = tab.dataset.tab;
        const filePath = tab.dataset.filePath;
        if (filePath) {
            tabsData.push({ id: tabId, filePath: filePath });
        }
    });
    localStorage.setItem('savedTabs', JSON.stringify(tabsData));
}

// 🔹 Загрузка вкладок из localStorage
async function loadTabsFromLocalStorage() {
    const savedTabs = JSON.parse(localStorage.getItem('savedTabs')) || [];
    if (savedTabs.length === 0) return;

    document.querySelectorAll('.tab').forEach(tab => tab.remove());
    document.querySelectorAll('.code-area[data-tab-content]').forEach(area => area.remove());
    codeMirrorInstances = {};

    for (const tabData of savedTabs) {
        const fileName = tabData.filePath.split('/').pop();
        const content = await loadFileContent(tabData.filePath);
        createNewTab(tabData.id, fileName, content, tabData.filePath, false);
    }

    const firstTab = document.querySelector('.tab');
    if (firstTab) {
        activateTab(firstTab);
    }
}

// 🔹 Обработчик клика на вкладки
tabs.addEventListener('click', (event) => {
    const tab = event.target.closest('.tab');
    if (!tab) return;
    if (event.target.classList.contains('close-tab')) {
        closeTab(tab);
        return;
    }
    activateTab(tab);
});

// 🔹 Инициализация
document.addEventListener('DOMContentLoaded', () => {
    const nightModeButton = document.querySelector('.night-mode');
    loadTabsFromLocalStorage();
    const savedTheme = localStorage.getItem('theme') === 'dark';
    updateCodeMirrorTheme(savedTheme);

    function updateCodeMirrorTheme(isDark) {
        const theme = isDark ? "dracula" : "default";
        for (const tabId in codeMirrorInstances) {
            if (codeMirrorInstances.hasOwnProperty(tabId)) {
                codeMirrorInstances[tabId].setOption("theme", theme);
            }
        }
    }

    function toggleCodeMirrorTheme() {
        if (!Object.keys(codeMirrorInstances).length) return;
        const currentTheme = codeMirrorInstances[Object.keys(codeMirrorInstances)[0]]
            .getOption("theme");
        updateCodeMirrorTheme(currentTheme !== "dracula");
    }

    if (nightModeButton) {
        nightModeButton.addEventListener('click', toggleCodeMirrorTheme);
    }

    // 🔹 Управление виртуальными окружениями
    const createVenvButton = document.createElement('button');
    createVenvButton.className = 'button';
    createVenvButton.innerHTML = '<i>Создать venv</i>';
    document.querySelector('.toolbar-left').appendChild(createVenvButton);

    createVenvButton.addEventListener('click', () => {
        const venvName = prompt('Введите имя виртуального окружения:', 'venv');
        if (venvName) {
            fetch('/api/venv', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrf_token')
                },
                body: JSON.stringify({ action: 'create', venv_name: venvName })
            })
                .then(response => response.json())
                .then(data => {
                    showNotification(data.message);
                })
                .catch(error => {
                    showNotification('Ошибка создания виртуального окружения');
                });
        }
    });
});

// 🔹 Удаляем автоматическое сохранение при каждом клике или вводе
window.addEventListener('beforeunload', saveTabsToLocalStorage);

// 🔹 Консоль и сокеты
function clearConsole() {
    localStorage.setItem("console", '');
    consoleOutput.value = "";
    consoleInput.classList.remove('console-input-active');
}

function executeCode() {
    clearConsole();
    const activeTab = document.querySelector('.tab.active');
    if (!activeTab) {
        consoleOutput.value += "\nОшибка: активная вкладка не найдена.";
        return;
    }
    const tabId = activeTab.dataset.tab;
    const activeEditor = codeMirrorInstances[tabId];
    if (!activeEditor) {
        consoleOutput.value += "\nОшибка: не найден редактор для активной вкладки.";
        return;
    }

    const filePath = activeTab.dataset.filePath;
    if (filePath) {
        const code = activeEditor.getValue();
        saveContentToFile(filePath, code);
        socket.emit('execute', {
            file_path: filePath,
            language: languageSelect.value,
            venv_name: 'venv' // Можно сделать выбор через интерфейс
        });
    } else {
        consoleOutput.value += "\nОшибка: путь к файлу не указан.";
    }
}

function appendToConsole(text) {
    consoleOutput.value += text + "\n";
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

socket.on('request_input', (prompt) => {
    appendToConsole(prompt);
    consoleInput.readOnly = false;
    updateConsoleInputClass();
    consoleInput.focus();
});

socket.on('console_output', (data) => {
    appendToConsole(data);
});

function handleConsoleKeyPress(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        const value = consoleInput.value.trim();
        if (value) {
            socket.emit('console_input', value);
            appendToConsole(value);
        }
        consoleInput.value = "";
        consoleInput.readOnly = true;
        consoleInput.classList.remove('console-input-active');
    }
}
consoleInput.addEventListener('keydown', handleConsoleKeyPress);

// 🔹 Уведомления
function showNotification(message) {
    const notification = document.createElement("div");
    notification.className = "notification";
    notification.innerText = message;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.opacity = 1;
    }, 10);
    setTimeout(() => {
        notification.style.opacity = 0;
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 3000);
}
