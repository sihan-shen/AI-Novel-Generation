var AgentChat = {
    send: function(e) {
        e.preventDefault();
        var input = document.getElementById('agent-input');
        var msg = input.value.trim();
        if (!msg) return false;
        var messages = document.getElementById('agent-chat-messages');
        var welcome = messages.querySelector('.agent-welcome');
        if (welcome) welcome.remove();
        var userEl = document.createElement('div');
        userEl.style.cssText = 'align-self:flex-end;background:var(--accent);color:var(--text-on-accent);padding:0.5rem 0.875rem;border-radius:12px 12px 0 12px;max-width:70%;font-size:0.875rem;';
        userEl.textContent = msg;
        messages.appendChild(userEl);
        input.value = '';
        input.disabled = true;
        document.getElementById('agent-send-btn').disabled = true;
        document.getElementById('agent-status').textContent = '运行中...';
        document.getElementById('agent-progress').style.display = 'block';
        document.getElementById('agent-progress-bar').style.width = '0%';
        var projectId = window.location.pathname.split('/')[2];
        var outlineId = document.getElementById('agent-outline-id').value;
        var targetWords = parseInt(document.getElementById('agent-target-words').value) || 3000;
        var lastSeq = 0;
        fetch('/project/' + projectId + '/agent/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg, chapter_outline_id: outlineId, target_words: targetWords}),
        }).then(function(response) {
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            var reader = response.body.getReader();
            var decoder = new TextDecoder();
            var buffer = '';
            function process() {
                reader.read().then(function(result) {
                    if (result.done) {
                        input.disabled = false;
                        document.getElementById('agent-send-btn').disabled = false;
                        document.getElementById('agent-status').textContent = '就绪';
                        document.getElementById('agent-progress').style.display = 'none';
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
                                if (data.sequence <= lastSeq) continue;
                                lastSeq = data.sequence;
                                AgentChat._handleEvent(currentEvent, data, messages);
                            } catch(e) { console.error(e); }
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
            input.disabled = false;
            document.getElementById('agent-send-btn').disabled = false;
            document.getElementById('agent-status').textContent = '连接失败: ' + err.message;
            document.getElementById('agent-progress').style.display = 'none';
        });
        return false;
    },
    _handleEvent: function(type, data, messages) {
        var el;
        switch (type) {
            case 'orchestrator_thought':
                el = document.createElement('div');
                el.style.cssText = 'font-size:0.75rem;color:var(--text-tertiary);font-style:italic;padding:0.25rem 0.5rem;';
                el.textContent = data.text;
                messages.appendChild(el);
                document.getElementById('agent-status').textContent = data.text;
                break;
            case 'agent_start':
                el = document.createElement('div');
                el.style.cssText = 'font-size:0.8125rem;color:var(--text-secondary);padding:0.5rem;border-left:2px solid var(--accent);';
                el.textContent = 'Agent 启动: ' + data.agent;
                messages.appendChild(el);
                if (data.agent === 'brainstorm') {
                    AgentChat._showBrainstormControls(true);
                    document.getElementById('agent-status').textContent = '脑暴中...';
                }
                break;
            case 'brainstorm_response':
                if (data.content) {
                    el = document.createElement('div');
                    el.className = 'agent-message brainstorm-response';
                    el.innerHTML = AgentChat._renderBrainstormContent(data.content);
                    messages.appendChild(el);
                }
                break;
            case 'brainstorm_end':
                AgentChat._showBrainstormControls(false);
                document.getElementById('agent-status').textContent = '就绪';
                if (data.pending_inspirations && data.pending_inspirations.length > 0) {
                    AgentChat._showInspirationPanel(data.pending_inspirations);
                }
                if (data.message && typeof showToast === 'function') {
                    showToast(data.message, data.timeout ? 'warning' : 'info');
                }
                break;
            case 'tool_call':
                el = document.createElement('div');
                el.style.cssText = 'background:var(--bg-hover);padding:0.5rem 0.75rem;border-radius:8px;font-size:0.8125rem;';
                el.innerHTML = '<details><summary style="cursor:pointer;">' + data.tool + '</summary><div style="margin-top:0.25rem;font-size:0.75rem;color:var(--text-secondary);">' + JSON.stringify(data.args) + '</div></details>';
                messages.appendChild(el);
                break;
            case 'tool_result':
                el = document.createElement('div');
                el.style.cssText = 'font-size:0.75rem;color:var(--text-secondary);padding:0.25rem 0.5rem;';
                el.textContent = data.summary || data.result;
                messages.appendChild(el);
                break;
            case 'agent_output':
                el = document.createElement('div');
                el.className = 'card';
                el.style.cssText = 'padding:0.75rem;';
                el.innerHTML = '<div class="heading-sm" style="margin:0 0 0.5rem 0;">Chapter Output</div><div style="font-size:0.8125rem;color:var(--text-secondary);">' + (data.preview || '') + '</div>';
                messages.appendChild(el);
                break;
            case 'task_complete':
                document.getElementById('agent-status').textContent = '完成: ' + data.summary;
                document.getElementById('agent-progress-bar').style.width = '100%';
                break;
            case 'error':
                el = document.createElement('div');
                el.style.cssText = 'color:var(--danger);font-size:0.8125rem;padding:0.5rem;';
                el.textContent = data.message;
                messages.appendChild(el);
                break;
        }
        messages.scrollTop = messages.scrollHeight;
    },

    _showBrainstormControls: function(show) {
        var container = document.getElementById('brainstorm-controls');
        if (!container) {
            container = document.createElement('div');
            container.id = 'brainstorm-controls';
            container.className = 'brainstorm-controls';
            container.style.cssText = 'display:flex;gap:0.5rem;align-items:center;padding:0.5rem 1rem;background:var(--bg-secondary);border-bottom:1px solid var(--border);';

            var indicator = document.createElement('span');
            indicator.className = 'brainstorm-indicator';
            indicator.style.cssText = 'font-size:0.8125rem;color:var(--text-secondary);flex:1;';

            var doneBtn = document.createElement('button');
            doneBtn.className = 'btn btn-sm btn-primary';
            doneBtn.textContent = '结束脑暴';
            var self = this;
            doneBtn.onclick = function() {
                self._sendCommand('/done');
            };

            var cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-sm btn-ghost';
            cancelBtn.textContent = '取消';
            cancelBtn.onclick = function() {
                self._sendCommand('/cancel');
            };

            container.appendChild(indicator);
            container.appendChild(doneBtn);
            container.appendChild(cancelBtn);

            var messages = document.getElementById('agent-chat-messages');
            messages.parentNode.insertBefore(container, messages);
        }
        container.style.display = show ? 'flex' : 'none';

        var indicator = container.querySelector('.brainstorm-indicator');
        if (indicator) indicator.textContent = '脑暴模式';
    },

    _sendCommand: function(cmd) {
        var input = document.getElementById('agent-input');
        if (input) {
            input.value = cmd;
            this.send(new Event('submit'));
        }
    },

    _renderBrainstormContent: function(text) {
        var html = text
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
        return '<p>' + html + '</p>';
    },

    _showInspirationPanel: function(inspirations) {
        var messages = document.getElementById('agent-chat-messages');
        var panel = document.createElement('div');
        panel.className = 'inspiration-panel card';
        panel.style.cssText = 'margin:1rem;padding:1rem;';

        var title = document.createElement('h4');
        title.className = 'heading-sm';
        title.textContent = '待保存的灵感 (' + inspirations.length + ')';
        panel.appendChild(title);

        for (var i = 0; i < inspirations.length; i++) {
            var insp = inspirations[i];
            var row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:flex-start;gap:0.5rem;padding:0.5rem 0;border-bottom:1px solid var(--border);';

            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = true;
            cb.dataset.inspId = insp.id;
            cb.style.cssText = 'margin-top:0.25rem;';

            var info = document.createElement('div');
            info.style.cssText = 'flex:1;';
            info.innerHTML = '<strong>' + insp.title + '</strong> <span style="color:var(--text-tertiary);font-size:0.75rem;">[' + insp.type + ']</span>' +
                '<div style="font-size:0.8125rem;color:var(--text-secondary);margin-top:0.25rem;">' + (insp.content || '').substring(0, 200) + '</div>';

            row.appendChild(cb);
            row.appendChild(info);
            panel.appendChild(row);
        }

        var actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:0.5rem;justify-content:flex-end;margin-top:0.75rem;';

        var saveBtn = document.createElement('button');
        saveBtn.className = 'btn btn-sm btn-primary';
        saveBtn.textContent = '保存选中';
        var self = this;
        saveBtn.onclick = function() {
            var checkboxes = panel.querySelectorAll('input[type=checkbox]');
            var selected = [];
            for (var j = 0; j < checkboxes.length; j++) {
                if (checkboxes[j].checked) selected.push(checkboxes[j].dataset.inspId);
            }
            AgentChat._confirmInspirations(selected);
            panel.remove();
        };

        var dismissBtn = document.createElement('button');
        dismissBtn.className = 'btn btn-sm btn-ghost';
        dismissBtn.textContent = '全部丢弃';
        dismissBtn.onclick = function() { panel.remove(); };

        actions.appendChild(dismissBtn);
        actions.appendChild(saveBtn);
        panel.appendChild(actions);

        messages.appendChild(panel);
        messages.scrollTop = messages.scrollHeight;
    },

    _confirmInspirations: function(inspIds) {
        var projectId = window.location.pathname.split('/')[2];
        fetch('/project/' + projectId + '/agent/inspirations/confirm', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({inspiration_ids: inspIds}),
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'ok' && typeof showToast === 'function') {
                showToast('已保存 ' + data.saved_count + ' 条灵感', 'success');
            }
        })
        .catch(function() {
            if (typeof showToast === 'function') showToast('保存失败', 'error');
        });
    },

    startNewSession: function() {
        this._showBrainstormControls(false);
    },
};
