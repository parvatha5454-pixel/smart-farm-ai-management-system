/* SmartFarm AI global UI: sidebar, search, notifications, toasts, confirm dialogs,
   form validation, table filters, chart defaults. All dynamic text uses textContent (no innerHTML). */
(function () {
    'use strict';
    const $ = (s, r) => (r || document).querySelector(s);
    const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
    function el(tag, cls, text) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text !== undefined) e.textContent = text;
        return e;
    }
    const csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

    // ---------- shared palette + chart defaults ----------
    const SF = window.SF = {
        csrf: csrf,
        palette: ['#167A50', '#C5E86C', '#123B2A', '#A8C5A0', '#0B6B63', '#B7791F', '#4F7A3A', '#7A8F83'],
        el: el,
        post: function (url, body) {
            return fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
                body: JSON.stringify(body || {})
            }).then(r => r.json().catch(() => ({ ok: false, error: 'Unexpected server response.' })));
        },
        get: function (url) {
            return fetch(url, { headers: { 'Accept': 'application/json' } }).then(r => r.json());
        }
    };
    if (window.Chart) {
        Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";
        Chart.defaults.color = '#5B6B61';
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.boxWidth = 8;
        Chart.defaults.plugins.tooltip.backgroundColor = '#123B2A';
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 10;
        Chart.defaults.maintainAspectRatio = false;
        Chart.defaults.borderColor = 'rgba(18,59,42,.08)';
    }
    // Show a message instead of a blank canvas when a chart has nothing to plot.
    SF.chart = function (id, config, hasData) {
        const canvas = document.getElementById(id);
        if (!canvas || !window.Chart) return null;
        if (!hasData) {
            const box = el('div', 'text-center text-muted small py-5', 'No data recorded yet for this chart.');
            canvas.replaceWith(box);
            return null;
        }
        return new Chart(canvas, config);
    };

    // ---------- toasts ----------
    const ICONS = { success: 'fa-circle-check', danger: 'fa-circle-exclamation', warning: 'fa-triangle-exclamation', info: 'fa-circle-info' };
    SF.toast = function (message, type) {
        type = ICONS[type] ? type : 'info';
        const stack = $('#toastStack');
        if (!stack) return;
        const t = el('div', 't-' + type + ' toast-item');
        t.setAttribute('role', type === 'danger' ? 'alert' : 'status');
        const ic = el('i', 'fa-solid t-ico ' + ICONS[type]);
        const msg = el('div', '', message);
        const x = el('button', '', '\u00d7');
        x.type = 'button'; x.setAttribute('aria-label', 'Dismiss');
        function close() { t.classList.add('leaving'); setTimeout(() => t.remove(), 260); }
        x.addEventListener('click', close);
        t.append(ic, msg, x);
        stack.appendChild(t);
        setTimeout(close, type === 'danger' ? 8000 : 5000);
    };
    $$('#flashData span').forEach(s => SF.toast(s.textContent, s.dataset.cat === 'error' ? 'danger' : s.dataset.cat));

    // ---------- sidebar ----------
    const body = document.body;
    const KEY = 'sf.sidebar';
    try { if (localStorage.getItem(KEY) === '1') body.classList.add('sidebar-collapsed'); } catch (e) { /* storage blocked */ }
    const collapseBtn = $('#collapseBtn');
    if (collapseBtn) collapseBtn.addEventListener('click', function () {
        const c = body.classList.toggle('sidebar-collapsed');
        collapseBtn.querySelector('i').className = 'fa-solid ' + (c ? 'fa-angles-right' : 'fa-angles-left');
        collapseBtn.setAttribute('aria-label', c ? 'Expand sidebar' : 'Collapse sidebar');
        try { localStorage.setItem(KEY, c ? '1' : '0'); } catch (e) { /* ignore */ }
    });
    if (collapseBtn && body.classList.contains('sidebar-collapsed')) collapseBtn.querySelector('i').className = 'fa-solid fa-angles-right';
    const menuBtn = $('#menuBtn');
    function closeMenu() { body.classList.remove('sidebar-open'); }
    if (menuBtn) menuBtn.addEventListener('click', () => body.classList.toggle('sidebar-open'));
    const backdrop = $('#sidebarBackdrop');
    if (backdrop) backdrop.addEventListener('click', closeMenu);
    $$('#sidebar a').forEach(a => a.addEventListener('click', closeMenu));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });

    // ---------- notifications ----------
    const notifList = $('#notifList');
    if (notifList && window.SF_URLS) {
        SF.get(SF_URLS.notifications).then(data => {
            notifList.textContent = '';
            const items = data.items || [];
            const dot = $('#notifDot');
            if (dot && items.length) { dot.textContent = items.length; dot.hidden = false; }
            if (!items.length) {
                notifList.appendChild(el('div', 'p-4 text-center text-muted small', 'You are all caught up.'));
                return;
            }
            items.forEach(i => {
                const a = el('a', 'notif-item'); a.href = i.url;
                const ico = el('span', 'ico tone-' + i.tone); ico.appendChild(el('i', 'fa-solid ' + i.icon));
                a.append(ico, el('span', '', i.text));
                notifList.appendChild(a);
            });
        }).catch(() => {
            notifList.textContent = '';
            notifList.appendChild(el('div', 'p-3 text-muted small', 'Notifications could not be loaded.'));
        });
    }

    // ---------- global search ----------
    const input = $('#globalSearch'), pop = $('#searchPop');
    if (input && pop && window.SF_URLS) {
        let timer = null, focusIdx = -1;
        function hide() { pop.hidden = true; focusIdx = -1; }
        function render(results) {
            pop.textContent = '';
            if (!results.length) { pop.appendChild(el('div', 'none', 'No matches. Try a different word.')); pop.hidden = false; return; }
            let group = null;
            results.forEach(r => {
                if (r.group !== group) { group = r.group; pop.appendChild(el('div', 'grp', group)); }
                const a = el('a'); a.href = r.url;
                a.appendChild(el('i', 'fa-solid ' + r.icon));
                a.appendChild(el('span', '', r.title));
                if (r.sub) a.appendChild(el('small', '', r.sub));
                pop.appendChild(a);
            });
            pop.hidden = false;
        }
        input.addEventListener('input', function () {
            clearTimeout(timer);
            const q = input.value.trim();
            if (q.length < 2) { hide(); return; }
            timer = setTimeout(() => {
                SF.get(SF_URLS.search + '?q=' + encodeURIComponent(q)).then(d => render(d.results || []))
                    .catch(() => { pop.textContent = ''; pop.appendChild(el('div', 'none', 'Search is unavailable right now.')); pop.hidden = false; });
            }, 200);
        });
        input.addEventListener('keydown', function (e) {
            const links = $$('a', pop);
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                if (!links.length) return;
                e.preventDefault();
                focusIdx = (focusIdx + (e.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
                links.forEach((l, i) => l.classList.toggle('focus', i === focusIdx));
            } else if (e.key === 'Enter' && focusIdx >= 0 && links[focusIdx]) {
                e.preventDefault(); links[focusIdx].click();
            } else if (e.key === 'Escape') { hide(); input.blur(); }
        });
        document.addEventListener('click', e => { if (!e.target.closest('.search-wrap')) hide(); });
        document.addEventListener('keydown', e => {
            const tag = (document.activeElement || {}).tagName;
            if ((e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(tag)) || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k')) {
                e.preventDefault(); input.focus(); input.select();
            }
        });
    }

    // ---------- delete confirmation dialog ----------
    const dlgEl = $('#confirmDeleteModal');
    if (dlgEl && window.bootstrap) {
        const dlg = new bootstrap.Modal(dlgEl);
        let pendingForm = null;
        $$('.confirm-delete-form').forEach(form => form.addEventListener('submit', function (e) {
            if (form.dataset.confirmed === '1') return;
            e.preventDefault();
            pendingForm = form;
            const name = form.getAttribute('data-item-name') || 'this record';
            $('#confirmDeleteTitle').textContent = 'Delete ' + name + '?';
            $('#confirmDeleteText').textContent = 'This cannot be undone.';
            dlg.show();
        }));
        $('#confirmDeleteYes').addEventListener('click', function () {
            if (!pendingForm) return;
            pendingForm.dataset.confirmed = '1';
            this.disabled = true;
            pendingForm.submit();
        });
    }

    // ---------- form validation ----------
    $$('form[method="POST"], form[method="post"]').forEach(form => {
        if (form.classList.contains('confirm-delete-form') || form.hasAttribute('data-no-validate')) return;
        form.setAttribute('novalidate', '');
        form.addEventListener('submit', function (e) {
            if (!form.checkValidity()) {
                e.preventDefault(); e.stopPropagation();
                form.classList.add('was-validated');
                const bad = form.querySelector(':invalid');
                $$(':invalid', form).forEach(f => {
                    const holder = f.parentElement;
                    let msg = holder.querySelector('.field-error');
                    if (!msg) { msg = el('div', 'field-error'); f.insertAdjacentElement('afterend', msg); }
                    msg.textContent = f.validationMessage || 'Please check this field.';
                });
                SF.toast('Please fix the highlighted fields.', 'danger');
                if (bad) bad.focus();
            } else {
                const btn = form.querySelector('button[type="submit"]:not([formaction])');
                if (btn && !btn.dataset.keepEnabled) setTimeout(() => { btn.disabled = true; }, 0);
            }
        });
        form.addEventListener('input', e => {
            const f = e.target; const msg = f.parentElement && f.parentElement.querySelector('.field-error');
            if (msg && f.checkValidity()) msg.textContent = '';
            else if (msg) msg.textContent = f.validationMessage;
        });
    });

    // ---------- live table filter ----------
    $$('[data-table-filter]').forEach(inp => {
        const target = document.querySelector(inp.dataset.tableFilter);
        if (!target) return;
        inp.addEventListener('input', function () {
            const q = inp.value.trim().toLowerCase();
            let shown = 0;
            $$('tbody tr', target).forEach(tr => {
                const hit = !q || tr.textContent.toLowerCase().indexOf(q) !== -1;
                tr.classList.toggle('row-hidden', !hit);
                if (hit) shown++;
            });
            const note = target.parentElement.querySelector('.filter-empty');
            if (note) note.hidden = shown !== 0;
        });
    });

    // Re-enable submit buttons if the page is restored from the back/forward cache.
    window.addEventListener('pageshow', e => { if (e.persisted) $$('button[type="submit"]:disabled').forEach(b => { b.disabled = false; }); });

    // ---------- tooltips ----------
    if (window.bootstrap) $$('[data-bs-toggle="tooltip"]').forEach(t => new bootstrap.Tooltip(t));
})();
