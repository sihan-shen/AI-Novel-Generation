/**
 * Global keyboard shortcut registry.
 *
 * Each entry: { keys: string, when: () => bool, do: () => void, label: string, group: string }
 * - keys: lowercase canonical form, e.g. "cmd+k", "g p", "esc"
 * - when: optional predicate; if false, the shortcut is skipped
 * - do: handler
 * - label: human description for the help modal
 * - group: section title in the help modal
 */
(function () {
    const isMac = navigator.platform.toUpperCase().includes('MAC');
    const MOD = isMac ? 'cmd' : 'ctrl';

    const shortcuts = [];

    function register(entry) {
        shortcuts.push(entry);
    }

    function isEditingTarget(el) {
        if (!el) return false;
        const tag = el.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA') return true;
        if (el.isContentEditable) return true;
        return false;
    }

    function getKey(e) {
        const parts = [];
        if (e.metaKey || e.ctrlKey) parts.push(isMac ? 'cmd' : 'ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        const k = e.key.toLowerCase();
        if (k === ' ') parts.push('space');
        else if (k.length === 1) parts.push(k);
        else parts.push(k);
        return parts.join('+');
    }

    let chord = '';
    let chordTimer = null;

    function clearChord() {
        chord = '';
        if (chordTimer) { clearTimeout(chordTimer); chordTimer = null; }
        const hint = document.getElementById('chord-hint');
        if (hint) hint.style.display = 'none';
    }

    function showChordHint(prefix) {
        let hint = document.getElementById('chord-hint');
        if (!hint) {
            hint = document.createElement('div');
            hint.id = 'chord-hint';
            hint.style.cssText = 'position:fixed;bottom:4rem;left:50%;transform:translateX(-50%);background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:0.5rem 1rem;font-family:monospace;font-size:0.875rem;box-shadow:var(--shadow-md);z-index:1000;';
            document.body.appendChild(hint);
        }
        hint.textContent = prefix + '...';
        hint.style.display = 'block';
    }

    document.addEventListener('keydown', function (e) {
        const editing = isEditingTarget(e.target);
        const key = getKey(e);

        const alwaysOn = new Set([
            `${MOD}+k`, `${MOD}+s`, `${MOD}+.`, `${MOD}+;`, `${MOD}+/`, 'escape',
        ]);

        if (!editing && key === 'g' && !chord) {
            chord = 'g';
            showChordHint('g ');
            chordTimer = setTimeout(clearChord, 800);
            e.preventDefault();
            return;
        }
        if (chord === 'g' && !editing) {
            const chordKey = `g ${key}`;
            const match = shortcuts.find(s => s.keys === chordKey && (!s.when || s.when()));
            clearChord();
            if (match) { e.preventDefault(); match.do(); }
            return;
        }

        if (editing && !alwaysOn.has(key)) return;

        const match = shortcuts.find(s => s.keys === key && (!s.when || s.when()));
        if (match) {
            e.preventDefault();
            match.do();
        }
    });

    window.Shortcuts = { register, list: () => shortcuts.slice(), MOD };
})();

// Defaults
Shortcuts.register({ keys: `${Shortcuts.MOD}+/`, group: '帮助', label: '显示快捷键帮助', do: () => window.openShortcutsHelp() });
Shortcuts.register({ keys: 'escape', group: '通用', label: '关闭模态/面板', do: () => {
    const help = document.getElementById('shortcuts-help-modal');
    if (help && help.style.display === 'flex') { help.style.display = 'none'; return; }
    const palette = document.getElementById('command-palette');
    if (palette && palette.style.display === 'flex') { palette.style.display = 'none'; return; }
}});
Shortcuts.register({ keys: `${Shortcuts.MOD}+s`, group: '写作', label: '强制立即保存', do: () => {
    document.dispatchEvent(new CustomEvent('novelforge:force-save'));
}});
Shortcuts.register({ keys: 'g p', group: '跳转', label: '跳转项目列表', do: () => window.location.href = '/' });
Shortcuts.register({ keys: 'g i', group: '跳转', label: '跳转灵感', do: () => window.location.href = '/ideas' });
Shortcuts.register({ keys: 'g b', group: '跳转', label: '跳转头脑风暴', do: () => window.location.href = '/brainstorm' });
Shortcuts.register({ keys: 'g h', group: '跳转', label: '跳转 AI 历史', do: () => window.location.href = '/ai-history' });

function currentProjectId() {
    const m = window.location.pathname.match(/\/projects?\/([^/]+)/);
    return m ? m[1] : null;
}
Shortcuts.register({ keys: 'g o', group: '跳转', label: '跳转当前项目大纲', when: () => !!currentProjectId(),
    do: () => window.location.href = `/project/${currentProjectId()}/outline` });
Shortcuts.register({ keys: 'g w', group: '跳转', label: '跳转当前项目写作', when: () => !!currentProjectId(),
    do: () => window.location.href = `/project/${currentProjectId()}/writer` });
Shortcuts.register({ keys: 'g s', group: '跳转', label: '跳转当前项目设定集', when: () => !!currentProjectId(),
    do: () => window.location.href = `/project/${currentProjectId()}/settings` });
Shortcuts.register({ keys: 'g r', group: '跳转', label: '跳转当前项目审阅', when: () => !!currentProjectId(),
    do: () => window.location.href = `/project/${currentProjectId()}/review` });
