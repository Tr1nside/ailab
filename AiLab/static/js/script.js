const body = document.body;
const tabs = document.querySelector('.tabs');
let codeMirrorInstances = {};
const consoleOutput = document.querySelector('.console-output');
const consoleInput = document.querySelector('.console-input');
const socket = io();

// 🔹 Список ключевых слов и встроенных функций Python для автодополнения
const pythonKeywords = [
    // 🔹 Ключевые слова Python
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",

    // 🔹 Встроенные функции Python
    "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "callable",
    "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir",
    "divmod", "enumerate", "eval", "exec", "filter", "float", "format",
    "frozenset", "getattr", "globals", "hasattr", "hash", "help", "hex",
    "id", "input", "int", "isinstance", "issubclass", "iter", "len",
    "list", "locals", "map", "max", "memoryview", "min", "next", "object",
    "oct", "open", "ord", "pow", "print", "property", "range", "repr",
    "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod",
    "str", "sum", "super", "tuple", "type", "vars", "zip",

    // 🔹 Базовые структуры данных
    "list", "tuple", "set", "frozenset", "dict",

    // 🔹 Структуры из модуля collections
    "deque", "defaultdict", "OrderedDict", "Counter", "ChainMap", "namedtuple",

    // 🔹 Структуры из модуля dataclasses
    "dataclass",

    // 🔹 Другие структуры данных
    "array", "heapq", "queue", "PriorityQueue",

    // 🔹 Часто используемые идентификаторы
    "self", "__init__", "__main__", "os", "sys", "json", "time", "re",
    "math", "random", "datetime", "open", "read", "write", "close"
];
    

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

// 🔹 Функция инициализации CodeMirror с настройками, как в VS Code
function initializeCodeMirror(codeArea, content = "") {
    const cm = CodeMirror(codeArea, {
        mode: "python",
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


consoleInput.addEventListener('focus', () => {
    if (consoleInput.readOnly) {
        consoleInput.blur(); // Убираем фокус, если поле readonly
    }
});

// Изначально поле ввода заблокировано
consoleInput.readOnly = true;

// Функция для обновления классов consoleInput
function updateConsoleInputClass() {
    if (consoleInput.readOnly) {
        consoleInput.classList.remove('console-input-active');
    } else {
        consoleInput.classList.add('console-input-active');
    }
}
updateConsoleInputClass();


// Функция для обновления номеров строк (если требуется)
function updateLineNumbers(cm, lineNumbers) {
    const numberOfLines = cm.lineCount();
    let numbers = "";
    for (let i = 1; i <= numberOfLines; i++) {
        numbers += i + "<br>";
    }
    lineNumbers.innerHTML = numbers;
}

// ======================================================================
// Новая логика работы вкладок
// ======================================================================

// Функция для поиска первого свободного номера вкладки
function getNextTabId() {
    const existingIds = new Set();
    document.querySelectorAll('.tab:not([data-tab="create_tab"])').forEach(tab => {
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
function createNewTab(customId = null, fileName = null, content = "", activate = true) {
    const newTabId = customId || getNextTabId();
    const newFileName = fileName || `file${newTabId.replace("tab", "")}.py`;

    const newTab = document.createElement('div');
    newTab.classList.add('tab');
    newTab.dataset.tab = newTabId;
    newTab.innerHTML = `<span>${newFileName}</span><span class="close-tab">×</span>
                        <input type="text" class="tab-input" value="${newFileName}">`;
    tabs.insertBefore(newTab, document.querySelector('.tab[data-tab="create_tab"]'));

    const codeArea = document.createElement('div');
    codeArea.classList.add('code-area');
    codeArea.dataset.tabContent = newTabId;
    document.querySelector('.container').insertBefore(codeArea, document.querySelector('.toolbar'));

    const cm = initializeCodeMirror(codeArea, content);
    codeMirrorInstances[newTabId] = cm;

    if (activate) activateTab(newTab);

    newTab.addEventListener('dblclick', () => startEditingTab(newTab));
    const inputElement = newTab.querySelector('.tab-input');
    inputElement.addEventListener('blur', () => finishEditingTab(newTab));
    inputElement.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') finishEditingTab(newTab);
    });
    saveTabsToLocalStorage();
}

window.createNewTabWithContent = function(fileName, content) {
    const newTabId = getNextTabId();
    createNewTab(newTabId, fileName, content, true);
};

// Функция для активации вкладки
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
}

// Функция для закрытия вкладки
function closeTab(tab) {
    const tabId = tab.dataset.tab;
    document.querySelector(`.tab[data-tab="${tabId}"]`).remove();
    document.querySelector(`.code-area[data-tab-content="${tabId}"]`).remove();
    delete codeMirrorInstances[tabId];
    const firstTab = document.querySelector('.tab:not([data-tab="create_tab"])');
    if (firstTab) {
        activateTab(firstTab);
    }
    saveTabsToLocalStorage();
}

// Функция для начала редактирования вкладки
function startEditingTab(tab) {
    tab.classList.add('editing');
    const inputElement = tab.querySelector('.tab-input');
    inputElement.style.display = 'block';
    inputElement.focus();
}

// Функция для завершения редактирования вкладки
function finishEditingTab(tab) {
    tab.classList.remove('editing');
    const inputElement = tab.querySelector('.tab-input');
    const spanElement = tab.querySelector('span');
    spanElement.textContent = inputElement.value;
    inputElement.style.display = 'none';
    saveTabsToLocalStorage();
}

// Функция для сохранения данных вкладок в localStorage
function saveTabsToLocalStorage() {
    const tabsData = [];
    document.querySelectorAll('.tab:not([data-tab="create_tab"])').forEach(tab => {
        const tabId = tab.dataset.tab;
        const fileName = tab.querySelector('span').textContent;
        const content = codeMirrorInstances[tabId] ? codeMirrorInstances[tabId].getValue() : "";
        tabsData.push({ id: tabId, name: fileName, content: content });
    });
    localStorage.setItem('savedTabs', JSON.stringify(tabsData));
}

// Функция для загрузки вкладок из localStorage
function loadTabsFromLocalStorage() {
    const savedTabs = JSON.parse(localStorage.getItem('savedTabs')) || [];
    if (savedTabs.length === 0) return;
    document.querySelectorAll('.tab:not([data-tab="create_tab"])').forEach(tab => tab.remove());
    document.querySelectorAll('.code-area[data-tab-content]').forEach(area => area.remove());
    codeMirrorInstances = {};
    savedTabs.forEach(tabData => {
        createNewTab(tabData.id, tabData.name, tabData.content, false);
    });
    activateTab(document.querySelector('.tab:not([data-tab="create_tab"])'));
}

// Обработчик клика на вкладки
tabs.addEventListener('click', (event) => {
    const tab = event.target.closest('.tab');
    if (!tab) return;
    if (event.target.classList.contains('close-tab')) {
        closeTab(tab);
        return;
    }
    if (tab.dataset.tab === 'create_tab') {
        createNewTab();
    } else {
        activateTab(tab);
    }
});
tabs.addEventListener('dblclick', (event) => {
    if (event.target.classList.contains('tab') && event.target.dataset.tab !== 'create_tab') {
        startEditingTab(event.target);
    }
});

// 🔹 Инициализация первой вкладки
const initialTab = document.querySelector('.tab[data-tab="tab1"]');
const initialCodeArea = document.querySelector('.code-area[data-tab-content="tab1"]');
codeMirrorInstances['tab1'] = initializeCodeMirror(initialCodeArea);
activateTab(initialTab);

initialTab.addEventListener('dblclick', function () { startEditingTab(this); });
const initialInputElement = initialTab.querySelector('.tab-input');
initialInputElement.addEventListener('blur', function () { finishEditingTab(initialTab); });
initialInputElement.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') finishEditingTab(initialTab);
});


// Вызываем загрузку вкладок при запуске
window.addEventListener('load', loadTabsFromLocalStorage);
window.addEventListener('beforeunload', saveTabsToLocalStorage);
document.addEventListener('input', saveTabsToLocalStorage);
document.addEventListener('click', saveTabsToLocalStorage);

// Отчистка консоли
function clearConsole() {
    localStorage.setItem("console", '')
    consoleOutput.value = "";
    consoleInput.classList.remove('console-input-active');
}

// Отправка кода на сервер
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
    const code = activeEditor.getValue();
    socket.emit('execute', code);
}
function appendToConsole(text) {
    consoleOutput.value += text;
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

socket.on('request_input', (prompt) => {
    appendToConsole(prompt + "\n"); // Выводим запрос в консоль
    consoleInput.readOnly = false;
    updateConsoleInputClass();
    consoleInput.focus();
});


socket.on('console_output', (data) => {
    appendToConsole(data + "\n");
});


function handleConsoleKeyPress(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        const value = consoleInput.value.trim();
        if (value) {
            socket.emit('console_input', value);
            appendToConsole(value + "\n");
        }
        consoleInput.value = "";
        consoleInput.readOnly = true;
        consoleInput.classList.remove('console-input-active');
    }
}
consoleInput.addEventListener('keydown', handleConsoleKeyPress);

// Сохранение кода из активного редактора в файл
function saveCodeToFile() {
    const activeTab = document.querySelector('.tab.active');
    if (!activeTab) {
        showNotification("Активная вкладка не найдена!");
        return;
    }
    const tabId = activeTab.dataset.tab;
    const editor = codeMirrorInstances[tabId];
    if (!editor) {
        showNotification("Редактор не найден!");
        return;
    }
    const codeContent = editor.getValue();
    const fileName = activeTab.querySelector('span').textContent || "code.txt";
    const blob = new Blob([codeContent], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = fileName;
    link.click();
}

// Сохранение вывода консоли в файл
function saveConsoleToFile() {
    const consoleContent = consoleOutput.value;
    const blob = new Blob([consoleContent], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "console_output.txt";
    link.click();
}

// Показ уведомления на экране
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

// Загрузка файла в активный редактор CodeMirror
function loadFile() {
    let fileInput = document.getElementById("fileInput");
    if (!fileInput) {
        fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.id = "fileInput";
        fileInput.style.display = "none";
        document.body.appendChild(fileInput);
    }
    fileInput.click();
    fileInput.onchange = function () {
        const file = fileInput.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function (event) {
            const activeTab = document.querySelector('.tab.active');
            if (!activeTab) {
                showNotification("Активная вкладка не найдена!");
                return;
            }
            const tabId = activeTab.dataset.tab;
            const editor = codeMirrorInstances[tabId];
            if (editor) {
                editor.setValue(event.target.result);
            }
        };
        reader.readAsText(file);
    };
}

// Копирование текста из консоли в буфер обмена
function copyToClipboard() {
    const text = consoleOutput.value;
    navigator.clipboard.writeText(text)
    .then(() => {
        showNotification("Текст скопирован в буфер обмена!");
    })
    .catch(err => {
        console.error("Ошибка при копировании: ", err);
    });
}



document.addEventListener("DOMContentLoaded", () => {
    const nightModeButton = document.querySelector('.night-mode');
    
    // Инициализация темы из localStorage
    const savedTheme = localStorage.getItem('theme') === 'dark';
    updateCodeMirrorTheme(savedTheme);

    // Функция для обновления темы CodeMirror
    function updateCodeMirrorTheme(isDark) {
        const theme = isDark ? "dracula" : "default";
        for (const tabId in codeMirrorInstances) {
            if (codeMirrorInstances.hasOwnProperty(tabId)) {
                codeMirrorInstances[tabId].setOption("theme", theme);
            }
        }
    }

    // Функция переключения темы
    function toggleCodeMirrorTheme() {
        if (!Object.keys(codeMirrorInstances).length) return;
        const currentTheme = codeMirrorInstances[Object.keys(codeMirrorInstances)[0]]
            .getOption("theme");
        updateCodeMirrorTheme(currentTheme !== "dracula");
    }

    if (nightModeButton) {
        nightModeButton.addEventListener('click', toggleCodeMirrorTheme);
    }
});