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
};
