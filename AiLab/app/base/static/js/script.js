const body = document.body;
const tabs = document.querySelector('.tabs');
let codeMirrorInstances = {};
const consoleOutput = document.querySelector('.console-output');
const consoleInput = document.querySelector('.console-input');
const socket = io();

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
    "self", "__init__", "__main__", " Piccolo ", "sys", "json", "time", "re",
    "math", "random", "datetime", "open", "read", "write", "close"
];

let saveInterval = null;

// 🔹 Управление меню opt-ver-menu
const optvermenu = document.querySelector('.opt-ver-menu');
const container = document.querySelector('.container');
optvermenu.hidden = true;
const optvermenutriger = document.querySelector('.opt-ver-menu-triger');
const optvermenutrigerreverse = document.querySelector('.opt-ver-menu-triger-reverse');

optvermenutriger.addEventListener("click", function() {
    container.hidden = true;
    document.querySelector(".console").hidden = true;
    optvermenu.hidden = false;
    
});

optvermenutrigerreverse.addEventListener("click", function() {
    optvermenu.hidden = true;
    container.hidden = false;
    document.querySelector(".console").hidden = false;
});

let setcounter = 1;
let currentSet = 'set1';
let currentPythonVersion = document.querySelector('.version-download').value || '3.12';
const setsData = {
    'set1': { libraries: [], python_version: '3.12' }
};
let libraries_massive = [];

function toggleCheck(element) {
    element.classList.toggle('checked');
    const libraryName = element.querySelector('span:first-child').textContent.trim();
    const index = setsData[currentSet].libraries.indexOf(libraryName);
    
    if (element.classList.contains('checked')) {
        if (index === -1) {
            setsData[currentSet].libraries.push(libraryName);
        }
    } else {
        if (index !== -1) {
            setsData[currentSet].libraries.splice(index, 1);
        }
    }
    savePreset(currentSet, setsData[currentSet].libraries, setsData[currentSet].python_version);
}

function selectSet(element) {
    document.querySelectorAll('.set').forEach(set => {
        set.classList.remove('active');
    });
    element.classList.add('active');
    currentSet = element.querySelector('span').textContent.trim();
    const setId = element.id;
    document.querySelectorAll(".libraries").forEach(libs => { libs.classList.remove('active'); });
    libraries_massive[setId - 1].classList.add("active");
    hideAllExcept();
    updateLibraryCheckboxes();
}

function addSet() {
    setcounter += 1;
    const setName = `set${setcounter}`;
    setsData[setName] = { libraries: [], python_version: currentPythonVersion };
    
    const newSet = document.createElement('div');
    newSet.className = 'set';
    newSet.insertAdjacentHTML('afterbegin', `<span>${setName}</span>`);
    newSet.setAttribute("ondblclick", "editSetName(this)");
    newSet.setAttribute("id", setcounter);
    document.querySelectorAll('.set').forEach(set => {
        set.classList.remove('active');
    });
    newSet.classList.add("active");
    newSet.onclick = function() { selectSet(this); };
    document.getElementById('sets-list').appendChild(newSet);
    
    create_new_group();
    hideAllExcept();
    currentSet = setName;
    savePreset(setName, [], currentPythonVersion);
}

function deleteSelectedSet() {
    if (document.querySelector(".sets").childElementCount > 1) {
        const selectedSet = document.querySelector('.set.active');
        const setName = selectedSet.querySelector('span').textContent.trim();
        selectedSet.remove();
        document.querySelector(".libraries.active").remove();
        libraries_massive = libraries_massive.filter((_, index) => index !== parseInt(selectedSet.id) - 1);
        fetch(`/delete_preset/${encodeURIComponent(setName)}`, {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showNotification(data.error);
                } else {
                    delete setsData[setName];
                    showNotification(`Пресет '${setName}' удален`);
                }
            })
            .catch(error => {
                showNotification(`Ошибка удаления пресета: ${error}`);
            });
    }
    if (document.querySelector(".set")) {
        const elcol = document.querySelectorAll('.set');
        const last_el = elcol[elcol.length - 1];
        last_el.classList.add("active");
        const last_el_id = last_el.id;
        libraries_massive[last_el_id - 1].classList.add("active");
        currentSet = last_el.querySelector('span').textContent.trim();
        hideAllExcept();
        updateLibraryCheckboxes();
    }
}

document.addEventListener('keydown', function(event) {
    if (event.code == 'Delete') {
        deleteSelectedSet();
    }
});

function editSetName(element) {
    const span = element.querySelector('span');
    if (!span) return;

    const oldName = span.textContent;
    const input = document.createElement('input');
    input.setAttribute("maxlength", "15");
    input.type = 'text';
    input.value = span.textContent;
    input.style.width = `9vw`;
    input.style.height = `2vh`;
    
    span.replaceWith(input);
    input.focus();

    function saveChanges() {
        const newName = input.value.trim() || oldName;
        const newSpan = document.createElement('span');
        newSpan.textContent = newName;
        input.replaceWith(newSpan);
        if (newName !== oldName) {
            fetch(`/delete_preset/${encodeURIComponent(oldName)}`, { method: 'DELETE' })
                .then(() => {
                    setsData[newName] = setsData[oldName];
                    delete setsData[oldName];
                    currentSet = newName;
                    savePreset(newName, setsData[newName].libraries, setsData[newName].python_version);
                });
        }
        input.removeEventListener('keydown', handleEnter);
        input.removeEventListener('blur', saveChanges);
    }

    function handleEnter(e) {
        if (e.key == 'Enter') {
            saveChanges();
        }
    }
    input.addEventListener('keydown', handleEnter);
    input.addEventListener('blur', saveChanges);
}

function hideAllExcept() {
    const elementsToHide = document.querySelectorAll(`.libraries:not(.active)`);
    elementsToHide.forEach(element => {
        element.style.display = 'none';
    });
    const elementsToShow = document.querySelectorAll(`.libraries.active`);
    elementsToShow.forEach(element => {
        element.style.display = 'block';
    });
}

function create_new_group() {
    const libraries_new = document.createElement('div');
    document.querySelectorAll(".libraries").forEach(libs => { libs.classList.remove('active'); });
    libraries_new.classList.add("libraries", "active");
    libraries_new.innerHTML = `
        <span class="labels-of-elements-libraries"><span>Библиотека</span><span>Версия</span><span>Последняя версия</span></span>
    `;
    fetch(`/libraries/${currentPythonVersion}`)
        .then(response => response.json())
        .then(libraries => {
            if (libraries.error) {
                showNotification(libraries.error);
                return;
            }
            libraries.forEach(lib => {
                const libElement = document.createElement('div');
                libElement.className = 'lib_element';
                libElement.setAttribute('ondblclick', 'toggleCheck(this)');
                libElement.innerHTML = `<span>${lib.name}</span><span>${lib.version}</span><span>${lib.version}</span>`;
                libraries_new.appendChild(libElement);
            });
            updateLibraryCheckboxes();
        })
        .catch(error => {
            showNotification(`Ошибка загрузки библиотек: ${error}`);
        });
    document.querySelector('.settings-options').appendChild(libraries_new);
    libraries_massive.push(libraries_new);
}

function loadPresets() {
    fetch('/presets')
        .then(response => response.json())
        .then(presets => {
            setcounter = 0;
            document.getElementById('sets-list').innerHTML = '';
            libraries_massive = [];
            document.querySelectorAll('.libraries').forEach(lib => lib.remove());
            Object.keys(setsData).forEach(setName => delete setsData[setName]);

            presets.forEach((preset, index) => {
                if (preset.python_version === currentPythonVersion) {
                    setcounter += 1;
                    const setName = preset.name;
                    setsData[setName] = { libraries: preset.libraries, python_version: preset.python_version };

                    const newSet = document.createElement('div');
                    newSet.className = `set${index === 0 ? ' active' : ''}`;
                    newSet.id = setcounter;
                    newSet.innerHTML = `<span>${setName}</span>`;
                    newSet.setAttribute("ondblclick", "editSetName(this)");
                    newSet.onclick = function() { selectSet(this); };
                    document.getElementById('sets-list').appendChild(newSet);

                    create_new_group();
                    if (index === 0) {
                        currentSet = setName;
                        updateLibraryCheckboxes();
                    }
                }
            });
            hideAllExcept();
            if (setcounter === 0) {
                addSet();
            }
        })
        .catch(error => {
            showNotification(`Ошибка загрузки пресетов: ${error}`);
        });
}

function savePreset(name, libraries, python_version) {
    fetch('/create_preset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, libraries, python_version })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error);
            } else {
                showNotification(`Пресет '${name}' сохранен`);
            }
        })
        .catch(error => {
            showNotification(`Ошибка сохранения пресета: ${error}`);
        });
}

function updateLibraryCheckboxes() {
    const activeLibraryDiv = document.querySelector('.libraries.active');
    if (!activeLibraryDiv) return;
    const libElements = activeLibraryDiv.querySelectorAll('.lib_element');
    libElements.forEach(element => {
        const libraryName = element.querySelector('span:first-child').textContent.trim();
        if (setsData[currentSet].libraries.includes(libraryName)) {
            element.classList.add('checked');
        } else {
            element.classList.remove('checked');
        }
    });
}

// Обработчик изменения версии Python
document.querySelector('.version-download').addEventListener('change', function() {
    currentPythonVersion = this.value;
    loadPresets();
});

// 🔹 Остальной код из вашего JS
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

function initializeCodeMirror(codeArea, content = "", filePath = null) {
    const cm = CodeMirror(codeArea, {
        mode: "python",
        theme: body.classList.contains('dark-mode') ? "material-darker" : "default",
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

    // Вставляем codeArea перед .toolbar внутри .part2-el
    const part2El = document.querySelector('.part2-el');
    const toolbar = document.querySelector('.toolbar');
    if (part2El && toolbar && part2El.contains(toolbar)) {
        part2El.insertBefore(codeArea, toolbar);
    } else {
        console.error('Ошибка: .part2-el или .toolbar не найдены или .toolbar не является дочерним для .part2-el');
        part2El.appendChild(codeArea); // Вставляем в конец, если не удалось перед .toolbar
    }

    const cm = initializeCodeMirror(codeArea, content, filePath);
    codeMirrorInstances[newTabId] = cm;

    if (activate) activateTab(newTab);

    saveTabsToLocalStorage();
}

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

tabs.addEventListener('click', (event) => {
    const tab = event.target.closest('.tab');
    if (!tab) return;
    if (event.target.classList.contains('close-tab')) {
        closeTab(tab);
        return;
    }
    activateTab(tab);
});

document.addEventListener('DOMContentLoaded', () => {
    const nightModeButton = document.querySelector('.night-mode');

    loadTabsFromLocalStorage();
    loadPresets();

    const savedTheme = localStorage.getItem('theme') === 'dark';
    updateCodeMirrorTheme(savedTheme);

    function updateCodeMirrorTheme(isDark) {
        const theme = isDark ? "material-darker" : "default";
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
        updateCodeMirrorTheme(currentTheme !== "material-darker");
    }

    if (nightModeButton) {
        nightModeButton.addEventListener('click', toggleCodeMirrorTheme);
    }
});

window.addEventListener('beforeunload', saveTabsToLocalStorage);

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
    const code = activeEditor.getValue();
    if (filePath) {
        fetch('/save_code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, file_path: filePath })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error);
            }
        })
        .catch(error => {
            showNotification(`Ошибка сохранения кода: ${error}`);
        });
    }

    userId = document.querySelector(".filetree-icon").dataset.userId;
    const presetName = currentSet;
    const pythonVersion = currentPythonVersion;
    const data = [userId, filePath, presetName, pythonVersion];
    socket.emit('execute', data);
}

function appendToConsole(text) {
    consoleOutput.value += text;
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

socket.on('request_input', (prompt) => {
    console.log("Received request_input with prompt:", prompt);
    appendToConsole(prompt + "\n");
    consoleInput.readOnly = false;
    updateConsoleInputClass();
    consoleInput.focus();
    setTimeout(() => consoleInput.focus(), 0);
});

socket.on('console_output', (data) => {
    console.log("Received console_output:", data);
    appendToConsole(data + "\n");
});

socket.on('connect_error', (error) => {
    console.error('Socket connection error:', error);
    showNotification('Ошибка соединения с сервером');
});

function handleConsoleKeyPress(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        const value = consoleInput.value.trim();
        console.log("Enter pressed, value:", value);
        if (value) {
            socket.emit('console_input', value);
            appendToConsole(value + "\n");
            console.log("Sent console_input:", value);
        } else {
            console.log("Empty input, skipping emit");
        }
        consoleInput.value = "";
        consoleInput.readOnly = true;
        updateConsoleInputClass();
    }
}

consoleInput.addEventListener('keydown', handleConsoleKeyPress);

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

// Инициализация первого набора
create_new_group();

document.querySelector('.console-close-button').addEventListener('click', function () {
    document.querySelector('.console').classList.toggle('close')
    document.querySelector('.CodeMirror').classList.toggle('console-close')
});
