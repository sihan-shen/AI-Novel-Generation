/**
 * Alpine.js component for the command palette.
 * Open/close via window.openPalette() / Cmd+K.
 */
function paletteComponent() {
    return {
        open: false,
        query: '',
        activeTab: 'all',
        tabs: [
            { id: 'all',     label: '全部' },
            { id: 'command', label: '命令' },
            { id: 'project', label: '项目' },
            { id: 'chapter', label: '章节' },
            { id: 'outline', label: '大纲' },
            { id: 'setting', label: '设定' },
            { id: 'idea',    label: '灵感' },
        ],
        results: [],
        loading: false,
        selectedIndex: 0,
        activeGroup: 'recent',

        init() {
            window.openPalette = () => this.openPalette();
            window.Shortcuts.register({
                keys: `${window.Shortcuts.MOD}+k`, group: '通用', label: '打开命令面板',
                do: () => this.openPalette(),
            });
        },

        get grouped() {
            var showAll = this.activeTab === 'all' || this.activeTab === 'command';
            var showRecent = this.activeTab === 'all';
            return {
                recent: showRecent ? (window.RecentItems ? window.RecentItems.list() : []).slice(0, 5) : [],
                commands: showAll ? this.filteredCommands().slice(0, 8) : [],
            };
        },

        filteredCommands() {
            var cmds = window.PaletteCommands ? window.PaletteCommands.all() : [];
            if (!this.query) return cmds;
            var fuse = new Fuse(cmds, { keys: ['title'], threshold: 0.4 });
            return fuse.search(this.query).map(function(r) { return r.item; });
        },

        openPalette() {
            this.open = true;
            this.query = '';
            this.results = [];
            this.activeTab = 'all';
            this.selectedIndex = 0;
            var recent = window.RecentItems ? window.RecentItems.list() : [];
            this.activeGroup = recent.length > 0 ? 'recent' : 'commands';
            this.$nextTick(function() { this.$refs.searchInput.focus(); }.bind(this));
        },

        close() { this.open = false; },

        setActiveTab(id) {
            this.activeTab = id;
            this.selectedIndex = 0;
            this.onQuery();
        },

        async onQuery() {
            var q = this.query.trim();
            if (!q) { this.results = []; return; }

            if (this.activeTab === 'command') {
                this.results = this.filteredCommands().map(function(c) {
                    return { type: 'command', id: c.id, title: c.title, _cmd: c };
                });
                return;
            }

            this.loading = true;
            var type = this.activeTab === 'all' ? 'all' : this.activeTab;
            try {
                var resp = await fetch('/api/search?q=' + encodeURIComponent(q) + '&type=' + type + '&limit=20');
                var body = await resp.json();
                var res = body.results || [];
                if (this.activeTab === 'all') {
                    var cmdMatches = this.filteredCommands().slice(0, 5).map(function(c) {
                        return { type: 'command', id: c.id, title: c.title, _cmd: c };
                    });
                    res = cmdMatches.concat(res);
                }
                this.results = res;
                this.activeGroup = 'results';
                this.selectedIndex = 0;
            } catch (e) {
                this.results = [];
                if (typeof showToast === 'function') showToast('搜索失败', 'error');
            } finally {
                this.loading = false;
            }
        },

        onKey(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                var item = this.currentItem();
                if (item) this.activate(item);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.moveSelection(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.moveSelection(-1);
            } else if (e.key === 'Tab') {
                e.preventDefault();
                var idx = this.tabs.findIndex(function(t) { return t.id === this.activeTab; }.bind(this));
                var next = e.shiftKey ? (idx - 1 + this.tabs.length) % this.tabs.length : (idx + 1) % this.tabs.length;
                this.setActiveTab(this.tabs[next].id);
            }
        },

        currentList() {
            if (this.query) return this.results;
            if (this.activeGroup === 'recent') return this.grouped.recent;
            return this.grouped.commands;
        },

        currentItem() {
            var list = this.currentList();
            return list[this.selectedIndex];
        },

        moveSelection(delta) {
            var list = this.currentList();
            if (!list.length) return;
            this.selectedIndex = (this.selectedIndex + delta + list.length) % list.length;
        },

        selectIndex(idx, group) {
            this.selectedIndex = idx;
            this.activeGroup = group;
        },

        activate(item) {
            this.close();
            if (item._cmd) { item._cmd.run(); return; }
            if (item.type === 'command') {
                var cmd = (window.PaletteCommands.all() || []).find(function(c) { return c.id === item.id; });
                if (cmd) cmd.run();
                return;
            }
            switch (item.type) {
                case 'project':   window.location.href = '/projects/' + item.id; break;
                case 'chapter':   window.location.href = '/project/' + item.project_id + '/writer?chapter=' + item.id; break;
                case 'outline':   window.location.href = '/projects/' + item.project_id; break;
                case 'writer':
                case 'settings':  window.location.href = '/projects/' + item.project_id; break;
                case 'setting':   window.location.href = '/project/' + item.project_id + '/settings/' + item.id; break;
                case 'idea':      window.location.href = '/ideas'; break;
            }
        },

        typeIcon(type) {
            return { project: '📚', chapter: '📖', outline: '📋', setting: '🌍', idea: '💡',
                     writer: '✍️', settings: '🌍', command: '⚡', agent: '✦' }[type] || '·';
        },

        relativeTime(ts) {
            if (!ts) return '';
            var diff = (Date.now() - ts) / 1000;
            if (diff < 60) return '刚刚';
            if (diff < 3600) return Math.floor(diff/60) + ' 分钟前';
            if (diff < 86400) return Math.floor(diff/3600) + ' 小时前';
            return Math.floor(diff/86400) + ' 天前';
        },
    };
}
