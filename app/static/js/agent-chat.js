/**
 * Agent Chat — SSE streaming, session management, collapsible event groups,
 * JSON formatting, and history rollback.
 */
var AgentChat = {
    /* ── State ── */
    currentTaskId: null,
    isHistorical: false,
    eventGroups: [],
    currentGroup: null,
    lastSeq: 0,

    /* ── Initialisation ── */
    init: function() {
        this.loadSessions();
    },

    /* ── Core: send message ── */
    send: function(e) {
        e.preventDefault();
        var input = document.getElementById('agent-input');
        var msg = input.value.trim();
        if (!msg) return false;
        var messages = this._msgContainer();
        var welcome = messages.querySelector('.agent-welcome');
        if (welcome) welcome.remove();

        // User bubble
        var userEl = document.createElement('div');
        userEl.className = 'agent-user-msg';
        userEl.textContent = msg;
        messages.appendChild(userEl);

        input.value = '';
        this._setInputEnabled(false);
        this._setStatus('运行中...');
        this._setProgress(true, 0);

        var projectId = window.location.pathname.split('/')[2];
        var outlineId = document.getElementById('agent-outline-id').value;
        var targetWords = parseInt(document.getElementById('agent-target-words').value) || 3000;
        this.lastSeq = 0;
        this.currentGroup = null;
        this.eventGroups = [];
        this.isHistorical = false;

        var self = this;
        fetch('/project/' + projectId + '/agent/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg, chapter_outline_id: outlineId, target_words: targetWords}),
        }).then(function(response) {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            var reader = response.body.getReader();
            var decoder = new TextDecoder();
            var buffer = '';
            function process() {
                reader.read().then(function(result) {
                    if (result.done) {
                        self._setInputEnabled(true);
                        self._setStatus('就绪');
                        self._setProgress(false);
                        self.loadSessions();
                        return;
                    }
                    buffer += decoder.decode(result.value, {stream: true});
                    var lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    var currentEvent = null;
                    for (var i = 0; i < lines.length; i++) {
                        var line = lines[i];
                        if (line.startsWith('event: ')) currentEvent = line.slice(7);
                        else if (line.startsWith('data: ') && currentEvent) {
                            try {
                                var data = JSON.parse(line.slice(6));
                                if (data.sequence <= self.lastSeq) continue;
                                self.lastSeq = data.sequence;
                                self._handleLiveEvent(currentEvent, data, messages);
                            } catch(ex) { console.error(ex); }
                            currentEvent = null;
                        }
                    }
                    process();
                }).catch(function(err) {
                    console.error('Stream error:', err);
                });
            }
            process();
        }).catch(function(err) {
            self._setInputEnabled(true);
            self._setStatus('连接失败: ' + err.message);
            self._setProgress(false);
        });
        return false;
    },

    /* ── Handle live SSE events ── */
    _handleLiveEvent: function(type, data, messages) {
        // Track task ID from reconnect or task_complete
        if (type === 'task_complete' && data.task_id) {
            this.currentTaskId = data.task_id;
        }
        if (type === 'reconnect' && data.task_id) {
            this.currentTaskId = data.task_id;
        }

        // Close current group on new agent_start or task end
        if (type === 'agent_start' && this.currentGroup) {
            this._closeGroup();
        }
        if ((type === 'task_complete' || type === 'done') && this.currentGroup) {
            this._closeGroup();
        }

        // Start new group on agent_start
        if (type === 'agent_start') {
            this._startGroup(data.agent, messages);
        }

        // Render the event
        var el = this._buildEventEl(type, data);
        if (el) {
            if (this.currentGroup && this._isGroupableEvent(type)) {
                this.currentGroup.body.appendChild(el);
            } else {
                messages.appendChild(el);
            }
            messages.scrollTop = messages.scrollHeight;
        }

        // Update status
        if (type === 'orchestrator_thought' && data.text) {
            this._setStatus(data.text);
        }
        if (type === 'task_complete') {
            this._setStatus('完成: ' + data.summary);
            this._setProgress(true, 100);
            this.currentTaskId = data.task_id || this.currentTaskId;
        }
        if (type === 'error' && data.message) {
            this._setStatus('错误: ' + data.message);
        }
        if (type === 'agent_output' || type === 'tool_result') {
            this._setProgress(true, Math.min(this.lastSeq * 3, 95));
        }
    },

    /* ── Event grouping ── */
    _startGroup: function(agentType, messages) {
        var group = document.createElement('div');
        group.className = 'agent-group ' + (agentType || 'writer');

        var header = document.createElement('div');
        header.className = 'agent-group-header';
        header.onclick = function() {
            group.classList.toggle('collapsed');
            var toggle = header.querySelector('.agent-group-toggle');
            if (toggle) toggle.textContent = group.classList.contains('collapsed') ? '▶' : '▼';
        };

        var toggle = document.createElement('span');
        toggle.className = 'agent-group-toggle';
        toggle.textContent = '▼';

        var badge = document.createElement('span');
        badge.className = 'agent-phase-badge ' + (agentType || 'writer');

        var label = document.createElement('span');
        var labels = { writer: '写作 Agent', reviewer: '审阅 Agent', settings_mgr: '设定 Agent' };
        label.textContent = labels[agentType] || (agentType + ' Agent');

        header.appendChild(toggle);
        header.appendChild(badge);
        header.appendChild(label);

        var body = document.createElement('div');
        body.className = 'agent-group-body';

        group.appendChild(header);
        group.appendChild(body);
        messages.appendChild(group);

        this.currentGroup = { el: group, header: header, body: body, type: agentType };
        this.eventGroups.push(this.currentGroup);
    },

    _closeGroup: function() {
        if (this.currentGroup) {
            this.currentGroup = null;
        }
    },

    _isGroupableEvent: function(type) {
        return ['orchestrator_thought', 'tool_call', 'tool_result', 'agent_start'].indexOf(type) !== -1;
    },

    toggleAllGroups: function(expand) {
        for (var i = 0; i < this.eventGroups.length; i++) {
            var g = this.eventGroups[i];
            g.el.classList.toggle('collapsed', !expand);
            var toggle = g.header.querySelector('.agent-group-toggle');
            if (toggle) toggle.textContent = expand ? '▼' : '▶';
        }
    },

    /* ── Build DOM element for an event ── */
    _buildEventEl: function(type, data) {
        switch (type) {
            case 'user_message':
                var el = document.createElement('div');
                el.className = 'agent-user-msg';
                el.textContent = data.text || data.content || '';
                return el;

            case 'orchestrator_thought':
                var el = document.createElement('div');
                el.className = 'agent-thought';
                el.textContent = data.text || '';
                return el;

            case 'agent_start':
                var el = document.createElement('div');
                el.className = 'agent-start';
                el.textContent = 'Agent 启动: ' + (data.agent || '');
                return el;

            case 'tool_call':
                var el = document.createElement('div');
                el.className = 'agent-tool-call';
                var details = document.createElement('details');
                details.open = true;
                var summary = document.createElement('summary');
                summary.textContent = data.tool || '工具调用';
                details.appendChild(summary);
                if (data.args) {
                    var jsonDiv = document.createElement('div');
                    jsonDiv.innerHTML = this.formatJSON(data.args);
                    details.appendChild(jsonDiv);
                }
                el.appendChild(details);
                return el;

            case 'tool_result':
                var el = document.createElement('div');
                el.className = 'agent-tool-result';
                el.textContent = data.summary || data.result || '';
                return el;

            case 'agent_output':
                var el = document.createElement('div');
                el.className = 'card agent-output';
                var title = document.createElement('div');
                title.className = 'heading-sm agent-output-title';
                title.textContent = data.agent === 'reviewer' ? '审阅结果' : '章节输出';
                el.appendChild(title);
                if (data.agent === 'reviewer' && data.data) {
                    var score = document.createElement('div');
                    score.style.cssText = 'font-size:0.875rem;margin-bottom:0.5rem;';
                    score.textContent = '综合评分: ' + (data.data.overall_score != null ? data.data.overall_score.toFixed(1) : 'N/A') + '/5.0';
                    el.appendChild(score);
                }
                var content = document.createElement('div');
                content.className = 'agent-output-content';
                content.textContent = data.preview || data.text || '';
                el.appendChild(content);

                // Rollback button for chapter drafts
                if (data.agent === 'writer' && data.chapter_id && this.currentTaskId) {
                    var rbBtn = document.createElement('button');
                    rbBtn.className = 'btn btn-sm btn-ghost';
                    rbBtn.style.cssText = 'margin-top:0.5rem;font-size:0.75rem;';
                    rbBtn.textContent = '回滚到此版本';
                    var self = this;
                    rbBtn.onclick = function() {
                        self._showRollbackDialog(data.chapter_id, self.currentTaskId);
                    };
                    el.appendChild(rbBtn);
                }
                return el;

            case 'task_complete':
                this._setProgress(true, 100);
                return null;

            case 'error':
                var el = document.createElement('div');
                el.className = 'agent-error';
                el.textContent = data.message || '发生错误';
                return el;

            default:
                return null;
        }
    },

    /* ── Session management ── */
    loadSessions: function() {
        var listEl = document.getElementById('agent-session-list');
        if (!listEl) return;
        var projectId = window.location.pathname.split('/')[2];

        listEl.innerHTML = '<div style="font-size:0.8125rem;color:var(--text-tertiary);padding:0.5rem;text-align:center;">加载中...</div>';

        var self = this;
        fetch('/project/' + projectId + '/agent/tasks?per_page=20')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data.tasks || data.tasks.length === 0) {
                    listEl.innerHTML = '<div style="font-size:0.8125rem;color:var(--text-tertiary);padding:0.5rem;text-align:center;">暂无历史</div>';
                    return;
                }
                listEl.innerHTML = '';
                for (var i = 0; i < data.tasks.length; i++) {
                    var item = self._buildSessionItem(data.tasks[i]);
                    listEl.appendChild(item);
                }
            })
            .catch(function() {
                listEl.innerHTML = '<div style="font-size:0.8125rem;color:var(--text-tertiary);padding:0.5rem;text-align:center;">加载失败</div>';
            });
    },

    _buildSessionItem: function(task) {
        var item = document.createElement('div');
        item.className = 'session-item';
        if (task.id === this.currentTaskId) item.classList.add('active');
        item.dataset.taskId = task.id;

        // Status badge
        var badge = document.createElement('span');
        badge.className = 'session-badge ' + (task.status || 'completed');
        var labels = { completed: '完成', running: '运行中', waiting_user: '待确认', cancelled: '已取消', error: '错误' };
        badge.textContent = labels[task.status] || task.status;
        item.appendChild(badge);

        // Info
        var info = document.createElement('div');
        info.className = 'session-info';
        var title = document.createElement('div');
        title.className = 'session-title';
        title.textContent = task.summary || task.task_type;
        info.appendChild(title);
        var time = document.createElement('div');
        time.className = 'session-time';
        time.textContent = this._relativeTime(task.created_at) + (task.message_count ? ' · ' + task.message_count + ' 条消息' : '');
        info.appendChild(time);
        item.appendChild(info);

        // Context menu trigger
        var menuBtn = document.createElement('button');
        menuBtn.className = 'btn btn-ghost btn-sm';
        menuBtn.textContent = '···';
        menuBtn.style.cssText = 'padding:0 0.25rem;font-size:0.75rem;';
        var self = this;
        menuBtn.onclick = function(e) {
            e.stopPropagation();
            self._showContextMenu(task, menuBtn);
        };
        item.appendChild(menuBtn);

        // Click to load
        item.onclick = function(e) {
            if (e.target === menuBtn) return;
            self.loadSessionMessages(task.id);
        };

        return item;
    },

    loadSessionMessages: function(taskId) {
        var projectId = window.location.pathname.split('/')[2];
        var messages = this._msgContainer();
        var self = this;

        // Show loading
        messages.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-tertiary);">加载历史会话...</div>';

        fetch('/project/' + projectId + '/agent/tasks/' + taskId + '/messages')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                messages.innerHTML = '';

                // Banner
                var banner = document.createElement('div');
                banner.className = 'session-history-banner';
                banner.innerHTML = '<span>📜 历史会话</span><button class="btn btn-sm btn-ghost" id="agent-back-to-live">回到当前</button>';
                messages.appendChild(banner);
                document.getElementById('agent-back-to-live').onclick = function() {
                    self.startNewSession();
                };

                // Disable input in historical mode
                self.isHistorical = true;
                self.currentTaskId = taskId;
                self.currentGroup = null;
                self.eventGroups = [];
                self._setInputEnabled(false);

                // Render each message
                for (var i = 0; i < data.messages.length; i++) {
                    var msg = data.messages[i];
                    var meta = msg.msg_metadata || {};
                    var eventData = meta;
                    if (!eventData.sequence) eventData.sequence = msg.sequence;
                    var el = self._buildEventEl(msg.message_type, eventData);
                    if (el) {
                        messages.appendChild(el);
                    }
                }
                messages.scrollTop = messages.scrollHeight;

                // Update session list active state
                var items = document.querySelectorAll('.session-item');
                for (var j = 0; j < items.length; j++) {
                    items[j].classList.toggle('active', items[j].dataset.taskId === taskId);
                }

                self._setStatus('浏览历史会话');
            })
            .catch(function() {
                messages.innerHTML = '<div class="agent-error">加载历史会话失败</div>';
            });
    },

    startNewSession: function() {
        var messages = this._msgContainer();
        messages.innerHTML =
            '<div class="agent-welcome empty-state">' +
            '<span class="empty-state-icon">✦</span>' +
            '<p class="empty-state-title">Agent 写作助手</p>' +
            '<p class="empty-state-desc">告诉我你想写哪一章、多少字，我会自动查询设定、创作正文。</p>' +
            '</div>';
        this.isHistorical = false;
        this.currentTaskId = null;
        this.currentGroup = null;
        this.eventGroups = [];
        this.lastSeq = 0;
        this._setInputEnabled(true);
        this._setStatus('就绪');

        // Clear active state in session list
        var items = document.querySelectorAll('.session-item.active');
        for (var i = 0; i < items.length; i++) items[i].classList.remove('active');
    },

    /* ── JSON formatting ── */
    formatJSON: function(obj) {
        if (obj === null || obj === undefined) return '<span class="json-null">null</span>';
        var html = this._jsonToHtml(obj, 0);
        return '<div class="json-block">' + html + '</div>';
    },

    _jsonToHtml: function(val, depth) {
        if (depth > 8) return '<span class="json-null">...</span>';

        if (val === null) return '<span class="json-null">null</span>';
        if (val === true) return '<span class="json-bool">true</span>';
        if (val === false) return '<span class="json-bool">false</span>';

        if (typeof val === 'number') return '<span class="json-number">' + val + '</span>';

        if (typeof val === 'string') {
            var escaped = val.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return '<span class="json-string">"' + escaped + '"</span>';
        }

        if (Array.isArray(val)) {
            if (val.length === 0) return '[]';
            var items = [];
            for (var i = 0; i < val.length && i < 20; i++) {
                items.push('<span style="display:block;padding-left:1.25rem;">' + this._jsonToHtml(val[i], depth + 1) + '</span>');
            }
            if (val.length > 20) items.push('<span style="display:block;padding-left:1.25rem;color:var(--text-tertiary);font-style:italic;">… 还有 ' + (val.length - 20) + ' 项</span>');
            return '[\n' + items.join(',\n') + '\n]';
        }

        if (typeof val === 'object') {
            var keys = Object.keys(val);
            if (keys.length === 0) return '{}';
            var items = [];
            for (var i = 0; i < keys.length; i++) {
                var k = keys[i];
                var v = this._jsonToHtml(val[k], depth + 1);
                items.push('<span style="display:block;padding-left:1.25rem;"><span class="json-key">"' + k + '"</span>: ' + v + '</span>');
            }
            return '{\n' + items.join(',\n') + '\n}';
        }

        return String(val);
    },

    /* ── Rollback UI ── */
    _showRollbackDialog: function(chapterId, taskId) {
        var overlay = document.createElement('div');
        overlay.className = 'rollback-dialog';
        overlay.innerHTML =
            '<div class="card" style="padding:1.5rem;">' +
            '<h3 class="heading-sm" style="margin:0 0 0.75rem 0;">回滚确认</h3>' +
            '<p style="font-size:0.8125rem;color:var(--text-secondary);margin-bottom:1rem;">将章节内容回滚到此版本？此操作不可撤销。</p>' +
            '<div id="rollback-diff-preview" class="rollback-diff">加载差异对比...</div>' +
            '<div style="display:flex;gap:0.5rem;justify-content:flex-end;margin-top:1rem;">' +
            '<button class="btn btn-ghost" id="rollback-cancel">取消</button>' +
            '<button class="btn btn-danger" id="rollback-confirm">确认回滚</button>' +
            '</div>' +
            '</div>';
        document.body.appendChild(overlay);

        document.getElementById('rollback-cancel').onclick = function() { overlay.remove(); };
        overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };

        // Load diff preview
        var projectId = window.location.pathname.split('/')[2];
        var self = this;
        fetch('/project/' + projectId + '/agent/tasks/' + taskId + '/chapter-diff?chapter_id=' + chapterId)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var preview = document.getElementById('rollback-diff-preview');
                if (data.error) {
                    preview.textContent = '无法加载差异: ' + data.error;
                } else {
                    preview.innerHTML = '<strong>变更摘要:</strong> ' + (data.summary || '无') +
                        '\n\n<strong>之前:</strong>\n' + (data.before_snippet || '无') +
                        '\n\n<strong>之后:</strong>\n' + (data.after_snippet || '无');
                }
            })
            .catch(function() {
                document.getElementById('rollback-diff-preview').textContent = '无法加载差异';
            });

        document.getElementById('rollback-confirm').onclick = function() {
            document.getElementById('rollback-confirm').disabled = true;
            document.getElementById('rollback-confirm').textContent = '回滚中...';
            fetch('/project/' + projectId + '/agent/tasks/' + taskId + '/restore-chapter', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({chapter_id: chapterId}),
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                overlay.remove();
                if (data.status === 'ok') {
                    if (typeof showToast === 'function') showToast('章节已回滚', 'success');
                } else {
                    if (typeof showToast === 'function') showToast('回滚失败: ' + (data.message || ''), 'error');
                }
            })
            .catch(function() {
                overlay.remove();
                if (typeof showToast === 'function') showToast('回滚请求失败', 'error');
            });
        };
    },

    _showContextMenu: function(task, anchor) {
        // Remove existing menus
        var old = document.querySelector('.context-menu');
        if (old) old.remove();

        var menu = document.createElement('div');
        menu.className = 'context-menu';
        menu.style.cssText = 'position:absolute;top:' + (anchor.getBoundingClientRect().bottom + 4) + 'px;left:' + Math.min(anchor.getBoundingClientRect().left, window.innerWidth - 160) + 'px;';

        var items = [
            { label: '加载会话', action: 'load' },
            { label: '查看产出', action: 'output' },
        ];
        if (task.status === 'completed') {
            items.push({ label: '重新运行', action: 'rerun' });
            items.push({ label: '回滚此版本', action: 'rollback', danger: true });
        }

        var self = this;
        for (var i = 0; i < items.length; i++) {
            var btn = document.createElement('button');
            btn.className = 'context-menu-item' + (items[i].danger ? ' danger' : '');
            btn.textContent = items[i].label;
            btn.onclick = (function(action) {
                return function() {
                    menu.remove();
                    self._handleContextAction(action, task);
                };
            })(items[i].action);
            menu.appendChild(btn);
        }

        document.body.appendChild(menu);

        // Click outside to close
        setTimeout(function() {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 0);
    },

    _handleContextAction: function(action, task) {
        switch (action) {
            case 'load':
                this.loadSessionMessages(task.id);
                break;
            case 'output':
                // Scroll to agent_output in the loaded session
                if (this.currentTaskId === task.id) {
                    var outputs = this._msgContainer().querySelectorAll('.agent-output');
                    if (outputs.length > 0) outputs[outputs.length - 1].scrollIntoView({ behavior: 'smooth' });
                } else {
                    this.loadSessionMessages(task.id);
                }
                break;
            case 'rerun':
                this._rerunTask(task);
                break;
            case 'rollback':
                // Find the agent_output event's chapter_id to pass to dialog
                this.loadSessionMessages(task.id);
                this._setStatus('请找到章节产出，点击"回滚到此版本"按钮');
                break;
        }
    },

    _rerunTask: function(task) {
        var projectId = window.location.pathname.split('/')[2];
        var self = this;
        fetch('/project/' + projectId + '/agent/tasks/' + task.id + '/rerun', {
            method: 'POST',
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'ok' && data.session_url) {
                window.location.href = data.session_url;
            } else if (data.status === 'ok' && data.new_task_id) {
                if (typeof showToast === 'function') showToast('已创建新任务', 'success');
                self.startNewSession();
            } else {
                if (typeof showToast === 'function') showToast('重新运行失败: ' + (data.message || ''), 'error');
            }
        })
        .catch(function() {
            if (typeof showToast === 'function') showToast('重新运行请求失败', 'error');
        });
    },

    /* ── Utility ── */
    _msgContainer: function() {
        return document.getElementById('agent-chat-messages');
    },

    _setInputEnabled: function(enabled) {
        var input = document.getElementById('agent-input');
        var btn = document.getElementById('agent-send-btn');
        if (input) input.disabled = !enabled;
        if (btn) btn.disabled = !enabled;
    },

    _setStatus: function(text) {
        var el = document.getElementById('agent-status');
        if (el) el.textContent = text;
    },

    _setProgress: function(show, pct) {
        var container = document.getElementById('agent-progress');
        var bar = document.getElementById('agent-progress-bar');
        if (container) container.style.display = show ? 'block' : 'none';
        if (bar && pct != null) bar.style.width = pct + '%';
    },

    _relativeTime: function(ts) {
        if (!ts) return '';
        var diff = (Date.now() - new Date(ts).getTime()) / 1000;
        if (diff < 60) return '刚刚';
        if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
        return Math.floor(diff / 86400) + ' 天前';
    },
};
