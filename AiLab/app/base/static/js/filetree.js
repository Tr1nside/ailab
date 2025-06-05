function isIdePage() {
    return window.location.pathname.startsWith('/ide');
}

document.addEventListener('DOMContentLoaded', function () {
    const filetreeButton = document.querySelector('.filetree-icon');
    const filetreeContainer = document.getElementById('filetree-container');
    const closeFiletree = document.getElementById('close-filetree');
    const filetreeContent = document.getElementById('filetree-content');
    const contextMenu = document.getElementById('filetreeContextMenu');
    const contextMenuList = document.getElementById('filetreeContextMenuList');

    document.addEventListener('click', hideContextMenu);
    
    if (!contextMenu || !contextMenuList) {
        console.error('Context menu elements not found:', { contextMenu, contextMenuList });
        return;
    }

    const contextMenuItems = {
        file: [
            { label: 'Открыть', action: 'read_file' },
            { label: 'Скачать', action: 'download_file' },
            { label: 'Копировать', action: 'copy' },
            { label: 'Переименовать', action: 'rename' },
            { label: 'Удалить', action: 'delete' },
        ],
        folder: [
            { label: 'Создать файл', action: 'create_file' },
            { label: 'Создать папку', action: 'create_folder' },
            { label: 'Копировать', action: 'copy' },
            { label: 'Переименовать', action: 'rename' },
            { label: 'Удалить', action: 'delete' },
        ],
        root: [
            { label: 'Создать файл', action: 'create_file' },
            { label: 'Создать папку', action: 'create_folder' },
        ],
    };

    function showContextMenu(x, y, type, element) {
        console.log('Showing context menu:', { x, y, type, element });
        const items = contextMenuItems[type] || [];
        contextMenuList.innerHTML = '';

        if (items.length === 0) {
            console.warn('No context menu items for type:', type);
            return;
        }

        items.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item.label;
            li.dataset.action = item.action;
            li.addEventListener('click', () => {
                handleContextMenuAction(item.action, element);
                hideContextMenu();
            });
            contextMenuList.appendChild(li);
        });

        const menuWidth = contextMenu.offsetWidth || 150;
        const menuHeight = contextMenu.offsetHeight || 100;
        const maxX = window.innerWidth - menuWidth;
        const maxY = window.innerHeight - menuHeight;

        contextMenu.style.left = `${Math.min(x, maxX)}px`;
        contextMenu.style.top = `${Math.min(y, maxY)}px`;
        contextMenu.style.zIndex = '9999';
        contextMenu.classList.add('visible');
        console.log('Context menu made visible:', {
            left: contextMenu.style.left,
            top: contextMenu.style.top,
            itemsCount: items.length,
        });
    }

    function hideContextMenu() {
        contextMenu.classList.remove('visible');
        console.log('Context menu hidden');
    }

    function handleContextMenuAction(action, element) {
        const path = element ? element.dataset.path : '';
        let postData;

        console.log('Handling action:', { action, path, element });

        switch (action) {
            case 'create_file':
                postData = {
                    action: 'create_file',
                    element: { path: path ? `${path}/new_file.py` : 'new_file.py' },
                };
                break;
            case 'create_folder':
                postData = {
                    action: 'create_folder',
                    element: { path: path ? `${path}/new_folder` : 'new_folder' },
                };
                break;
            case 'rename':
                const nameElement = element.querySelector('.name');
                const oldName = nameElement.textContent;
                const textarea = document.createElement('textarea');
                textarea.value = oldName;
                textarea.className = 'rename-textarea';
                nameElement.style.display = 'none';
                element.insertBefore(textarea, nameElement.nextSibling);
                textarea.focus();

                textarea.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const newName = textarea.value.trim();
                        if (newName && newName !== oldName) {
                            const parentPath = path.substring(0, path.lastIndexOf('/'));
                            const newPath = parentPath ? `${parentPath}/${newName}` : newName;
                            fetch('/api/file-action', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': getCookie('csrf_token'),
                                },
                                body: JSON.stringify({
                                    action: 'rename',
                                    element: { old_path: path, new_path: newPath },
                                }),
                            })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.status === 'success') {
                                        loadFileTree();
                                        window.updateTabsOnRename(path, newPath); // Обновляем вкладки
                                    } else {
                                        alert(`Ошибка: ${data.message}`);
                                    }
                                })
                                .catch(error => {
                                    console.error('Ошибка:', error);
                                    alert('Не удалось переименовать');
                                })
                                .finally(() => {
                                    textarea.remove();
                                    nameElement.style.display = '';
                                });
                        } else {
                            textarea.remove();
                            nameElement.style.display = '';
                        }
                    }
                });
                return;
            case 'delete':
                postData = {
                    action: 'delete',
                    element: { path: path },
                };
                break;
            case 'copy':
                const srcName = element.querySelector('.name').textContent;
                const copyName = prompt('Введите имя копии:', `copy_of_${srcName}`);
                if (!copyName) return;
                const parentPathCopy = path.substring(0, path.lastIndexOf('/'));
                const destPath = parentPathCopy ? `${parentPathCopy}/${copyName}` : copyName;
                postData = {
                    action: 'copy',
                    element: { src_path: path, dest_path: destPath },
                };
                break;
            case 'read_file':
                postData = {
                    action: 'read_file',
                    element: { path: path },
                };
                break;
            case 'download_file':
                postData = {
                    action: 'download_file',
                    element: { path: path },
                };
                window.location.href = `/api/file-action?action=download_file&path=${encodeURIComponent(path)}`;
                return;
            default:
                console.warn('Unknown action:', action);
                return;
        }

        fetch('/api/file-action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrf_token'),
            },
            body: JSON.stringify(postData),
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data);
                if (data.status === 'success') {
                    if (action === 'read_file') {
                        window.openFileInTab(path, data.content);
                    } else {
                        loadFileTree();
                    }
                } else {
                    alert(`Ошибка: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
                alert('Не удалось выполнить действие');
            });
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function loadFileTree() {
        fetch('/api/filetree', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    renderFileTree(data.filetree, filetreeContent);
                } else {
                    filetreeContent.innerHTML = '<p>Ошибка загрузки файлов: ' + data.error + '</p>';
                }
            })
            .catch(error => {
                filetreeContent.innerHTML = '<p>Ошибка: ' + error.message + '</p>';
            });
    }

    function renderFileTree(items, parentElement) {
        parentElement.innerHTML = '';
        const ul = document.createElement('ul');
        ul.className = 'filetree-list';
    
        items.forEach(item => {
            const li = document.createElement('li');
            li.className = 'tree-item' + (item.type === 'folder' && item.children.length ? ' has-children' : '');
            li.dataset.path = item.path;
            li.dataset.type = item.type;
            li.draggable = true;
    
            const icon = document.createElement('span');
            icon.className = 'icon';
            icon.textContent = item.type === 'folder' ? '📁' : '📄';
    
            const name = document.createElement('span');
            name.className = 'name';
            name.textContent = item.name;
    
            li.appendChild(icon);
            li.appendChild(name);
    
            let childrenUl;
            if (item.type === 'folder' && item.children.length) {
                childrenUl = document.createElement('ul');
                childrenUl.className = 'filetree-list';
                childrenUl.style.display = 'none';
                renderFileTree(item.children, childrenUl);
                li.appendChild(childrenUl);
            }
    
            li.addEventListener('click', (e) => {
                e.stopPropagation();
    
                if (li.dataset.type === 'folder') {
                    const isOpen = li.classList.contains('open');
                    li.classList.toggle('open', !isOpen);
                    icon.textContent = isOpen ? '📁' : '📂';
                    if (childrenUl) {
                        childrenUl.style.display = isOpen ? 'none' : 'block';
                    }
                } else if (li.dataset.type === 'file') {
                    document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('selected'));
                    li.classList.add('selected');
                }
            });

            li.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                const extension = li.dataset.path.split('.').pop().toLowerCase();
                const imageExtensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'];
                const isImage = imageExtensions.includes(extension);
                console.log('Двойной клик на:', li.dataset.path, 'Расширение:', extension, 'Это изображение:', isImage);

                if (li.dataset.type === 'file' && !isImage) {
                    // Существующая логика для не-изображений
                    const postData = {
                        action: 'read_file',
                        element: { path: li.dataset.path },
                    };
                    fetch('/api/file-action', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrf_token'),
                        },
                        body: JSON.stringify(postData),
                    })
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`HTTP error! Status: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(data => {
                            console.log('Ответ сервера:', data);
                            if (data.status === 'success') {
                                window.openFileInTab(li.dataset.path, data.content);
                            } else {
                                showNotification(`Ошибка: ${data.message}`);
                            }
                        })
                        .catch(error => {
                            console.error('Ошибка при загрузке файла:', error);
                            showNotification('Не удалось загрузить файл');
                        });
                } else {
                    const userId = document.querySelector(".filetree-icon").dataset.userId
                    const imagePath = window.getUserFileUrl(userId, li.dataset.path);
                    console.log(imagePath);
                    
                    // Создаем div с фоновым изображением
                    const overlayDiv = document.createElement('div');
                    overlayDiv.style.cssText = `
                        background: rgba(0, 0, 0, 0.75) url("${imagePath}") center center / contain no-repeat;
                        width: 100%;
                        height: 100%;
                        position: fixed;
                        top: 0px;
                        left: 0px;
                        z-index: 10000;
                        cursor: zoom-out;
                    `;
                    
                    // Добавляем обработчик клика для закрытия
                    overlayDiv.addEventListener('click', function() {
                        document.body.removeChild(overlayDiv);
                    });
                    
                    // Вставляем div в body
                    document.body.appendChild(overlayDiv);
                }
            });
    
            li.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                e.stopPropagation();
                showContextMenu(e.clientX, e.clientY, li.dataset.type, li);
            });
    
            li.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', item.path);
                li.classList.add('dragging');
            });
    
            li.addEventListener('dragend', () => {
                li.classList.remove('dragging');
            });
    
            li.addEventListener('dragover', (e) => {
                e.preventDefault();
                if (item.type === 'folder') {
                    li.classList.add('drag-over');
                }
            });
    
            li.addEventListener('dragleave', () => {
                li.classList.remove('drag-over');
            });
    
            li.addEventListener('drop', (e) => {
                e.preventDefault();
                li.classList.remove('drag-over');
                if (item.type === 'file') return;
            
                const srcPath = e.dataTransfer.getData('text/plain');
                const srcName = srcPath.split('/').pop();
                
                if (item.path.startsWith(srcPath + '/') || item.path === srcPath) {
                    alert('Невозможно переместить папку внутрь себя или своего подкаталога');
                    return;
                }
                
                const destPath = `${item.path}/${srcName}`;
            
                fetch('/api/file-action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrf_token'),
                    },
                    body: JSON.stringify({
                        action: 'move',
                        element: { src_path: srcPath, dest_path: destPath },
                    }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        loadFileTree();
                        window.updateTabsOnRename(srcPath, destPath); // Обновляем вкладки при перемещении
                    } else {
                        alert(`Ошибка: ${data.message}`);
                    }
                })
                .catch(error => {
                    console.error('Ошибка:', error);
                    alert('Не удалось переместить элемент');
                });
            });
    
            ul.appendChild(li);
        });
    
        parentElement.appendChild(ul);
    
        parentElement.dataset.type = 'root';
        parentElement.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            showContextMenu(e.clientX, e.clientY, parentElement.dataset.type, null);
        });
    }
    

    filetreeButton.addEventListener('click', function () {
        filetreeContainer.classList.toggle('open');
        if (filetreeContainer.classList.contains('open')) {
            loadFileTree();
        }
        if (isIdePage()) {
            document.querySelector('.part2-el').classList.toggle('open-filetree');
        }
    });

    if (closeFiletree) {
        closeFiletree.addEventListener('click', function () {
            filetreeContainer.classList.remove('open');
            if (isIdePage()) {
                document.querySelector('.part2-el').classList.remove('open-filetree');
            }
        });
    }
});
