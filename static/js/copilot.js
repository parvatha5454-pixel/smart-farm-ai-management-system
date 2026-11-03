// AI Copilot page. All dynamic text uses textContent (never innerHTML) to prevent XSS.
(function () {
    const csrf = document.querySelector('meta[name="csrf-token"]').content;
    const chatBox = document.getElementById('chatBox');
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const activity = document.getElementById('activity');
    const pendingArea = document.getElementById('pendingArea');
    const quickResult = document.getElementById('quickResult');
    const modalEl = document.getElementById('confirmModal');
    const modal = new bootstrap.Modal(modalEl);
    let currentAction = null;
    let currentCard = null;

    function el(tag, cls, text) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text !== undefined) e.textContent = text;
        return e;
    }

    function api(url, body) {
        return fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
            body: JSON.stringify(body || {})
        }).then(r => r.json().catch(() => ({ok: false, error: 'Unexpected server response.'})));
    }

    // ---- light, safe formatting of assistant replies (bold, bullets, Facts / Recommendations blocks)
    function inline(parent, text) {
        text.split(/\*\*/).forEach((part, i) => {
            if (!part) return;
            parent.appendChild(i % 2 ? el('strong', '', part) : document.createTextNode(part));
        });
    }
    function formatInto(target, raw) {
        target.textContent = '';
        let container = target, list = null;
        (raw || '').split(/\r?\n/).forEach(line => {
            const t = line.trim();
            if (!t) { list = null; return; }
            const head = t.replace(/^#+\s*/, '').replace(/\*\*/g, '').replace(/:$/, '');
            if (/^facts\b/i.test(head) && head.length < 60) {
                container = el('div', 'fact-block'); container.appendChild(el('span', 'block-tag', 'Facts from your records'));
                target.appendChild(container); list = null; return;
            }
            if (/^recommendations\b/i.test(head) && head.length < 70) {
                container = el('div', 'rec-block'); container.appendChild(el('span', 'block-tag', 'Suggestions, not facts'));
                target.appendChild(container); list = null; return;
            }
            const m = t.match(/^(?:[-*\u2022]|\d+[.)])\s+(.*)$/);
            if (m) {
                if (!list) { list = el('ul'); container.appendChild(list); }
                const li = el('li'); inline(li, m[1]); list.appendChild(li);
            } else {
                list = null;
                const p = el('p'); inline(p, t); container.appendChild(p);
            }
        });
    }
    document.querySelectorAll('.chat-msg[data-format]').forEach(m => formatInto(m, m.textContent));

    function scrollDown() { chatBox.scrollTop = chatBox.scrollHeight; }

    function addMessage(role, text) {
        const empty = document.getElementById('chatEmpty');
        if (empty) empty.remove();
        const row = el('div', 'chat-row ' + role);
        const av = el('span', 'chat-avatar');
        if (role === 'user') av.textContent = window.USER_INITIAL || 'U'; else av.appendChild(el('i', 'fa-solid fa-leaf'));
        const msg = el('div', 'chat-msg ' + role);
        if (role === 'assistant') formatInto(msg, text); else msg.textContent = text;
        row.append(av, msg);
        chatBox.appendChild(row);
        scrollDown();
        return row;
    }

    function typingRow() {
        const row = el('div', 'chat-row assistant');
        const av = el('span', 'chat-avatar'); av.appendChild(el('i', 'fa-solid fa-leaf'));
        const msg = el('div', 'chat-msg assistant');
        const dots = el('div', 'typing'); dots.setAttribute('aria-label', 'Copilot is checking your farm data');
        dots.append(el('i'), el('i'), el('i'));
        msg.append(dots, el('div', 'small text-muted', 'Checking your farm data...'));
        row.append(av, msg); chatBox.appendChild(row); scrollDown();
        return row;
    }

    // ---- tool activity chips
    const STATUS = {
        ok: ['', 'checked'],
        error: ['err', 'could not run'],
        denied: ['deny', 'not allowed'],
        pending_confirmation: ['wait', 'waiting for your approval']
    };
    function showActivity(list) {
        activity.textContent = '';
        (list || []).forEach(a => {
            const s = STATUS[a.status] || STATUS.error;
            activity.appendChild(el('span', 'badge tool-chip me-1 ' + s[0], a.label + ': ' + s[1]));
        });
    }

    // ---- pending proposal cards (approve / reject)
    function addPendingCard(a) {
        const card = el('div', 'action-card mb-2');
        const tag = el('div', 'ac-tag'); tag.append(el('i', 'fa-solid fa-hourglass-half'), document.createTextNode('Proposed change, not saved yet'));
        card.appendChild(tag);
        card.appendChild(el('div', 'ac-prev', a.preview));
        if (a.reason) card.appendChild(el('div', 'small text-muted', a.reason));
        const btns = el('div', 'mt-2 d-flex gap-2 flex-wrap');
        const review = el('button', 'btn btn-sm btn-success', 'Review and approve');
        review.type = 'button';
        const reject = el('button', 'btn btn-sm btn-outline-secondary', 'Reject');
        reject.type = 'button';
        review.addEventListener('click', () => {
            currentAction = a; currentCard = card;
            document.getElementById('confirmPreview').textContent = a.preview;
            document.getElementById('confirmReason').textContent = a.reason || '';
            modal.show();
        });
        reject.addEventListener('click', () => {
            reject.disabled = true;
            api('/copilot/actions/' + a.id + '/reject').then(r => finishCard(card, r));
        });
        btns.append(review, reject);
        card.appendChild(btns);
        pendingArea.appendChild(card);
    }

    function finishCard(card, r) {
        card.textContent = '';
        card.className = 'action-card mb-2 ' + (r.ok ? 'done-ok' : 'done-err');
        card.appendChild(el('div', 'fw-semibold', r.ok ? r.message : (r.error || 'Something went wrong.')));
        if (window.SF) SF.toast(r.ok ? r.message : (r.error || 'Something went wrong.'), r.ok ? 'success' : 'danger');
    }

    document.getElementById('confirmYes').addEventListener('click', () => {
        if (!currentAction) return;
        const btn = document.getElementById('confirmYes');
        btn.disabled = true;
        api('/copilot/actions/' + currentAction.id + '/confirm').then(r => {
            modal.hide();
            finishCard(currentCard, r);
        }).finally(() => { btn.disabled = false; });
    });

    (window.INITIAL_PENDING || []).forEach(addPendingCard);
    scrollDown();

    // ---- sending messages
    function send(text) {
        text = (text || '').trim();
        if (!text) return;
        addMessage('user', text);
        input.value = '';
        sendBtn.disabled = true; input.disabled = true;
        activity.textContent = '';
        const loading = typingRow();

        api('/copilot/chat', {message: text}).then(r => {
            loading.remove();
            if (r.reply) addMessage('assistant', r.reply);
            else addMessage('assistant', r.error || 'Something went wrong. Please try again.');
            showActivity(r.tool_activity);
            (r.pending_actions || []).forEach(addPendingCard);
        }).catch(() => {
            loading.remove();
            addMessage('assistant', 'Could not reach the server. Check your connection and try again.');
        }).finally(() => {
            sendBtn.disabled = false; input.disabled = false; input.focus();
        });
    }

    sendBtn.addEventListener('click', () => send(input.value));
    input.addEventListener('keydown', e => { if (e.key === 'Enter') send(input.value); });
    document.querySelectorAll('.prompt-card').forEach(b =>
        b.addEventListener('click', () => send(b.dataset.prompt)));

    // ---- quick data buttons (no AI)
    function render(value, depth) {
        if (Array.isArray(value)) {
            if (!value.length) return el('div', 'text-muted', 'None');
            if (value.every(v => v && typeof v === 'object' && !Array.isArray(v))) {
                const keys = Object.keys(value[0]).filter(k => typeof value[0][k] !== 'object' || value[0][k] === null);
                const wrap = el('div', 'table-responsive');
                const t = el('table', 'table table-sm');
                const thead = el('thead'); const hr = el('tr');
                keys.forEach(k => hr.appendChild(el('th', '', k.replace(/_/g, ' '))));
                thead.appendChild(hr); t.appendChild(thead);
                const tb = el('tbody');
                value.forEach(row => {
                    const tr = el('tr');
                    keys.forEach(k => tr.appendChild(el('td', '', row[k] === null ? '-' : String(row[k]))));
                    tb.appendChild(tr);
                });
                t.appendChild(tb); wrap.appendChild(t); return wrap;
            }
            const ul = el('ul', 'mb-1');
            value.forEach(v => { const li = el('li'); li.appendChild(render(v, depth + 1)); ul.appendChild(li); });
            return ul;
        }
        if (value && typeof value === 'object') {
            const dl = el('dl', 'mb-1');
            Object.keys(value).forEach(k => {
                dl.appendChild(el('dt', 'text-capitalize', k.replace(/_/g, ' ')));
                const dd = el('dd', 'mb-1'); dd.appendChild(render(value[k], depth + 1)); dl.appendChild(dd);
            });
            return dl;
        }
        return document.createTextNode(value === null ? '-' : String(value));
    }

    document.querySelectorAll('.quick-btn').forEach(b => b.addEventListener('click', () => {
        quickResult.textContent = '';
        const sk = el('div', 'skeleton'); sk.style.height = '60px'; quickResult.appendChild(sk);
        api('/copilot/quick/' + b.dataset.tool, {}).then(r => {
            quickResult.textContent = '';
            if (!r.ok) { quickResult.appendChild(el('div', 'note danger', r.error || 'Could not load data.')); return; }
            quickResult.appendChild(el('div', 'fw-semibold mb-1', r.label));
            quickResult.appendChild(render(r.data, 0));
        }).catch(() => { quickResult.textContent = 'Could not reach the server.'; });
    }));
})();
