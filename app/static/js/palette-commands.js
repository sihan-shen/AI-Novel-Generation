/**
 * Built-in command registry for the command palette.
 *
 * Each entry: { id, title, group, when?: () => bool, run: () => void, shortcut?: string }
 */
(function () {
    function currentProjectId() {
        const m = window.location.pathname.match(/\/projects?\/([^/]+)/);
        return m ? m[1] : null;
    }

    const commands = [
        { id: 'goto-projects', title: '跳转项目列表', group: '导航', shortcut: 'g p',
          run: () => window.location.href = '/' },
        { id: 'goto-styles', title: '跳转文风库', group: '导航',
          run: () => window.location.href = '/styles' },
        { id: 'goto-brainstorm', title: '跳转头脑风暴', group: '导航', shortcut: 'g b',
          run: () => window.location.href = '/brainstorm' },
        { id: 'goto-ideas', title: '跳转灵感', group: '导航', shortcut: 'g i',
          run: () => window.location.href = '/ideas' },
        { id: 'goto-config', title: '跳转配置', group: '导航',
          run: () => window.location.href = '/config' },
        { id: 'project-outline', title: '当前项目 · 大纲', group: '项目', shortcut: 'g o',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/outline` },
        { id: 'project-writer', title: '当前项目 · 写作', group: '项目', shortcut: 'g w',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/writer` },
        { id: 'project-settings', title: '当前项目 · 设定集', group: '项目', shortcut: 'g s',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/settings` },
        { id: 'project-review', title: '当前项目 · 审阅', group: '项目', shortcut: 'g r',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/review` },
        { id: 'project-agent', title: '当前项目 · Agent 写作', group: '项目', shortcut: 'g a',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/agent` },
        { id: 'toggle-theme', title: '切换主题（明/暗）', group: '外观',
          run: () => window.toggleTheme() },
        { id: 'shortcuts-help', title: '查看快捷键帮助', group: '帮助',
          shortcut: window.Shortcuts ? `${window.Shortcuts.MOD}+/` : '⌘/',
          run: () => window.openShortcutsHelp() },
        { id: 'new-project', title: '新建项目', group: '操作',
          run: () => { window.location.href = '/'; setTimeout(() => {
              const btn = document.querySelector('[hx-get="/projects/new"]');
              if (btn) btn.click();
          }, 100); }},
    ];

    window.PaletteCommands = { all: () => commands.filter(c => !c.when || c.when()) };
})();
