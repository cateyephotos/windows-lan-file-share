// ===== State =====
let currentFolder = '';
let sortColumn = 'name';
let sortDirection = 'asc';
let viewMode = localStorage.getItem('viewMode') || 'list';

// allFiles and allFolders are injected by the server via template substitution
// const allFiles = __FILES_JSON__;
// const allFolders = __FOLDERS_JSON__;

const fileTypeMap = {
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'],
    'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
    'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
    'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
    'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']
};

const textExtensions = [
    '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.yaml', '.yml',
    '.toml', '.ini', '.cfg', '.conf', '.c', '.cpp', '.h', '.hpp', '.java', '.go',
    '.rs', '.rb', '.php', '.sh', '.bat', '.ps1', '.ts', '.tsx', '.jsx', '.vue',
    '.svelte', '.csv', '.log', '.sql', '.gitignore', '.env', '.dockerfile',
    '.makefile', '.cmake', '.gradle', '.properties', '.r', '.swift', '.kt',
    '.scala', '.pl', '.lua', '.zig', '.nim', '.ex', '.exs', '.clj'
];

// ===== Utilities =====
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function getFileIcon(extension) {
    if (fileTypeMap.image.includes(extension)) return '🖼️';
    if (fileTypeMap.video.includes(extension)) return '🎬';
    if (fileTypeMap.audio.includes(extension)) return '🎵';
    if (fileTypeMap.document.includes(extension)) return '📄';
    if (fileTypeMap.archive.includes(extension)) return '📦';
    return '📄';
}

function getFileType(extension) {
    for (let [type, exts] of Object.entries(fileTypeMap)) {
        if (exts.includes(extension)) return type;
    }
    return 'other';
}

function isTextFile(ext) {
    return textExtensions.includes(ext);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ===== Theme =====
function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        document.documentElement.dataset.theme = 'dark';
        const icon = document.getElementById('themeIcon');
        if (icon) icon.textContent = '☀️';
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.dataset.theme === 'dark';
    html.dataset.theme = isDark ? 'light' : 'dark';
    document.getElementById('themeIcon').textContent = isDark ? '🌙' : '☀️';
    localStorage.setItem('theme', html.dataset.theme);
}

// ===== View Mode =====
function initViewMode() {
    const fileList = document.querySelector('.file-list');
    if (viewMode === 'grid') {
        fileList.classList.add('grid-view');
    }
    updateViewButtons();
}

function setViewMode(mode) {
    viewMode = mode;
    localStorage.setItem('viewMode', mode);
    document.querySelector('.file-list').classList.toggle('grid-view', mode === 'grid');
    updateViewButtons();
    filterFiles();
}

function updateViewButtons() {
    var listBtn = document.getElementById('listViewBtn');
    var gridBtn = document.getElementById('gridViewBtn');
    if (listBtn) listBtn.classList.toggle('active', viewMode === 'list');
    if (gridBtn) gridBtn.classList.toggle('active', viewMode === 'grid');
}

// ===== Sorting =====
function setSort(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    updateSortIndicators();
    filterFiles();
}

function updateSortIndicators() {
    ['name', 'size', 'modified'].forEach(function(col) {
        var el = document.getElementById('sort-' + col);
        if (el) {
            el.textContent = '';
            el.classList.remove('active');
        }
    });
    var active = document.getElementById('sort-' + sortColumn);
    if (active) {
        active.textContent = sortDirection === 'asc' ? '▲' : '▼';
        active.classList.add('active');
    }
}

function sortFiles(files) {
    return files.slice().sort(function(a, b) {
        var cmp = 0;
        switch (sortColumn) {
            case 'name':
                cmp = a.name.localeCompare(b.name, undefined, {sensitivity: 'base'});
                break;
            case 'size':
                cmp = a.sizeBytes - b.sizeBytes;
                break;
            case 'modified':
                cmp = a.modified.localeCompare(b.modified);
                break;
        }
        return sortDirection === 'asc' ? cmp : -cmp;
    });
}

function sortFolderNames(folders) {
    return folders.slice().sort(function(a, b) {
        var nameA = a.split('/').pop();
        var nameB = b.split('/').pop();
        var cmp = nameA.localeCompare(nameB, undefined, {sensitivity: 'base'});
        if (sortColumn === 'name') {
            return sortDirection === 'asc' ? cmp : -cmp;
        }
        return cmp;
    });
}

// ===== Folder Navigation =====
function navigateToFolder(folder) {
    currentFolder = folder;
    updateBreadcrumb();
    filterFiles();
    window.scrollTo(0, 0);
}

function goUp() {
    if (!currentFolder) return;
    var lastSlash = currentFolder.lastIndexOf('/');
    if (lastSlash === -1) {
        navigateToFolder('');
    } else {
        navigateToFolder(currentFolder.substring(0, lastSlash));
    }
}

function updateBreadcrumb() {
    var breadcrumb = document.getElementById('breadcrumb');
    var btnUp = document.getElementById('btnUp');

    if (btnUp) {
        btnUp.disabled = !currentFolder;
    }

    // Keep the Up button, clear the rest
    while (breadcrumb.children.length > 1) {
        breadcrumb.removeChild(breadcrumb.lastChild);
    }

    var homeLink = document.createElement('a');
    homeLink.href = '#';
    homeLink.textContent = '🏠 Home';
    homeLink.onclick = function(e) { e.preventDefault(); navigateToFolder(''); };
    breadcrumb.appendChild(homeLink);

    if (currentFolder) {
        var parts = currentFolder.split('/');
        var path = '';
        for (var i = 0; i < parts.length; i++) {
            path += (path ? '/' : '') + parts[i];

            var sep = document.createElement('span');
            sep.textContent = '/';
            breadcrumb.appendChild(sep);

            var link = document.createElement('a');
            link.href = '#';
            link.textContent = parts[i];
            var navPath = path;
            link.onclick = (function(p) {
                return function(e) { e.preventDefault(); navigateToFolder(p); };
            })(navPath);
            breadcrumb.appendChild(link);
        }
    }
}

// ===== File Filtering & Rendering =====
function filterFiles() {
    var searchTerm = document.getElementById('searchBox').value.toLowerCase();
    var typeFilter = document.getElementById('typeFilter').value;

    var container = document.getElementById('fileContainer');
    container.innerHTML = '';

    var fragment = document.createDocumentFragment();

    // Get subfolders in current folder
    var subfolders = allFolders.filter(function(f) {
        if (!currentFolder) {
            return !f.includes('/') && f !== '';
        } else {
            return f.startsWith(currentFolder + '/') &&
                   f.split('/').length === currentFolder.split('/').length + 1;
        }
    });

    // Get files in current folder
    var filesInFolder = allFiles.filter(function(f) { return f.folder === currentFolder; });

    // Apply search/type filters
    var filteredFiles = filesInFolder.filter(function(f) {
        var matchesSearch = f.name.toLowerCase().includes(searchTerm);
        var matchesType = !typeFilter || getFileType(f.extension) === typeFilter;
        return matchesSearch && matchesType;
    });

    // Sort
    subfolders = sortFolderNames(subfolders);
    filteredFiles = sortFiles(filteredFiles);

    // Render folders
    subfolders.forEach(function(folder) {
        var folderName = folder.split('/').pop();
        var div = document.createElement('div');
        div.className = 'folder-item';
        div.onclick = function() { navigateToFolder(folder); };

        if (viewMode === 'grid') {
            div.innerHTML =
                '<div class="file-icon">📁</div>' +
                '<div class="file-name" title="' + escapeHtml(folderName) + '">' + escapeHtml(folderName) + '</div>' +
                '<div class="file-size"></div>';
        } else {
            div.innerHTML =
                '<div class="file-icon">📁</div>' +
                '<div class="file-name" title="' + escapeHtml(folderName) + '">' + escapeHtml(folderName) + '</div>' +
                '<div class="file-size"></div>' +
                '<div class="file-modified"></div>' +
                '<div class="file-actions"></div>';
        }
        fragment.appendChild(div);
    });

    // Render files
    filteredFiles.forEach(function(file) {
        var div = document.createElement('div');
        div.className = 'file-item';

        var iconHtml;
        var isImage = fileTypeMap.image.includes(file.extension);

        if (viewMode === 'grid' && isImage) {
            iconHtml = '<img src="/files/' + encodeURIComponent(file.id) + '" alt="" class="grid-thumbnail" loading="lazy">';
        } else if (viewMode === 'list' && isImage) {
            iconHtml = '<img src="/files/' + encodeURIComponent(file.id) + '" alt="" class="list-thumbnail" loading="lazy">';
        } else {
            iconHtml = getFileIcon(file.extension);
        }

        var fileIdEnc = encodeURIComponent(file.id);
        var fileNameEsc = escapeHtml(file.name);
        var fileSizeEsc = escapeHtml(file.size);
        var fileModEsc = escapeHtml(file.modified);
        var fileExt = file.extension;

        if (viewMode === 'grid') {
            div.innerHTML =
                '<div class="file-icon">' + iconHtml + '</div>' +
                '<div class="file-name" title="' + fileNameEsc + '">' + fileNameEsc + '</div>' +
                '<div class="file-size">' + fileSizeEsc + '</div>' +
                '<div class="file-actions">' +
                    '<a href="/download/' + fileIdEnc + '" class="action-btn action-download" onclick="event.stopPropagation();">⬇️</a>' +
                    '<button class="action-btn action-preview" onclick="event.stopPropagation(); openPreview(\'' + file.id.replace(/'/g, "\\'") + '\', \'' + file.name.replace(/'/g, "\\'").replace(/\\/g, '\\\\') + '\', \'' + fileExt + '\')">👁️</button>' +
                '</div>';
        } else {
            div.innerHTML =
                '<div class="file-icon">' + iconHtml + '</div>' +
                '<div class="file-name" title="' + fileNameEsc + '">' + fileNameEsc + '</div>' +
                '<div class="file-size">' + fileSizeEsc + '</div>' +
                '<div class="file-modified">' + fileModEsc + '</div>' +
                '<div class="file-actions">' +
                    '<a href="/download/' + fileIdEnc + '" class="action-btn action-download" onclick="event.stopPropagation();">⬇️</a>' +
                    '<button class="action-btn action-preview" onclick="event.stopPropagation(); openPreview(\'' + file.id.replace(/'/g, "\\'") + '\', \'' + file.name.replace(/'/g, "\\'").replace(/\\/g, '\\\\') + '\', \'' + fileExt + '\')">👁️</button>' +
                '</div>';
        }

        fragment.appendChild(div);
    });

    // Batch append
    container.appendChild(fragment);

    // Update stats
    var totalItems = subfolders.length + filteredFiles.length;
    var totalSize = filteredFiles.reduce(function(sum, f) { return sum + f.sizeBytes; }, 0);
    var sizeStr = formatBytes(totalSize);

    document.getElementById('stats').textContent =
        totalItems + ' item(s) | ' + filteredFiles.length + ' file(s) | Total: ' + sizeStr;

    if (totalItems === 0) {
        container.innerHTML = '<div class="no-files">No files found</div>';
    }
}

function clearFilters() {
    document.getElementById('searchBox').value = '';
    document.getElementById('typeFilter').value = '';
    filterFiles();
}

// ===== Preview Modal =====
function openPreview(fileId, fileName, extension) {
    var modal = document.getElementById('previewModal');
    var content = document.getElementById('modalContent');
    var title = document.getElementById('modalTitle');
    var downloadLink = document.getElementById('modalDownload');

    title.textContent = fileName;
    downloadLink.href = '/download/' + encodeURIComponent(fileId);
    content.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-secondary);">Loading...</div>';
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    var fileUrl = '/files/' + encodeURIComponent(fileId);
    var ext = extension.toLowerCase();

    if (fileTypeMap.image.includes(ext)) {
        var img = document.createElement('img');
        img.className = 'preview-image';
        img.alt = fileName;
        img.src = fileUrl;
        content.innerHTML = '';
        content.appendChild(img);

    } else if (fileTypeMap.video.includes(ext)) {
        content.innerHTML =
            '<video controls autoplay style="max-width:100%;max-height:70vh;display:block;margin:0 auto;border-radius:4px;">' +
            '<source src="' + fileUrl + '">' +
            'Your browser does not support video playback.' +
            '</video>';

    } else if (fileTypeMap.audio.includes(ext)) {
        content.innerHTML =
            '<div class="audio-preview">' +
            '<div class="audio-icon">🎵</div>' +
            '<div class="audio-name">' + escapeHtml(fileName) + '</div>' +
            '<audio controls autoplay style="width:100%;max-width:500px;"><source src="' + fileUrl + '"></audio>' +
            '</div>';

    } else if (ext === '.pdf') {
        content.innerHTML = '<iframe class="preview-pdf" src="' + fileUrl + '"></iframe>';

    } else if (isTextFile(ext)) {
        fetch(fileUrl)
            .then(function(r) { return r.text(); })
            .then(function(text) {
                var lines = text.split('\n');
                var maxLines = 5000;
                var truncated = lines.length > maxLines;
                var displayLines = truncated ? lines.slice(0, maxLines) : lines;

                var table = document.createElement('table');
                for (var i = 0; i < displayLines.length; i++) {
                    var tr = document.createElement('tr');
                    var tdNum = document.createElement('td');
                    tdNum.className = 'line-number';
                    tdNum.textContent = i + 1;
                    var tdContent = document.createElement('td');
                    tdContent.className = 'line-content';
                    tdContent.textContent = displayLines[i];
                    tr.appendChild(tdNum);
                    tr.appendChild(tdContent);
                    table.appendChild(tr);
                }

                var wrapper = document.createElement('div');
                wrapper.className = 'code-preview';
                wrapper.appendChild(table);

                content.innerHTML = '';
                content.appendChild(wrapper);

                if (truncated) {
                    var notice = document.createElement('div');
                    notice.className = 'truncation-notice';
                    notice.textContent = 'Showing first ' + maxLines + ' of ' + lines.length + ' lines. Download the file to see the full content.';
                    content.appendChild(notice);
                }
            })
            .catch(function() {
                content.innerHTML = '<div class="no-preview"><p>Failed to load file preview</p></div>';
            });

    } else {
        content.innerHTML =
            '<div class="no-preview">' +
            '<div class="no-preview-icon">📎</div>' +
            '<p>No preview available for this file type (' + escapeHtml(ext) + ')</p>' +
            '<a href="/download/' + encodeURIComponent(fileId) + '" class="btn btn-primary" style="margin-top:8px;">⬇️ Download File</a>' +
            '</div>';
    }
}

function closePreviewModal() {
    var modal = document.getElementById('previewModal');
    modal.style.display = 'none';
    document.body.style.overflow = '';
    // Stop any playing media
    var video = modal.querySelector('video');
    var audio = modal.querySelector('audio');
    if (video) video.pause();
    if (audio) audio.pause();
}

// ===== Keyboard Navigation =====
document.addEventListener('keydown', function(e) {
    // Close modal on Escape
    if (e.key === 'Escape') {
        var modal = document.getElementById('previewModal');
        if (modal && modal.style.display === 'flex') {
            closePreviewModal();
            return;
        }
    }
    // Folder navigation
    if (e.altKey && e.key === 'ArrowUp') {
        e.preventDefault();
        goUp();
    }
    if (e.key === 'Backspace' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        goUp();
    }
});

// Close modal on overlay click
document.addEventListener('click', function(e) {
    if (e.target && e.target.id === 'previewModal') {
        closePreviewModal();
    }
});

// ===== Initialization =====
function init() {
    initTheme();
    initViewMode();
    updateSortIndicators();
    filterFiles();
}

init();
