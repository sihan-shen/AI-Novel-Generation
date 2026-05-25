/**
 * Track recently-visited items in localStorage.
 *
 * Storage key: novelforge-recent
 * Structure: [{type, id, title, project_id, project_title, ts}, ...] (max 20, newest first)
 */
(function () {
    const KEY = 'novelforge-recent';
    const MAX = 20;

    function load() {
        try { return JSON.parse(localStorage.getItem(KEY) || '[]'); }
        catch (e) { return []; }
    }

    function save(items) {
        localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX)));
    }

    function record(item) {
        if (!item || !item.type || !item.id) return;
        let items = load();
        items = items.filter(i => !(i.type === item.type && i.id === item.id));
        items.unshift({ ...item, ts: Date.now() });
        save(items);
    }

    function list() {
        return load();
    }

    function clear() {
        localStorage.removeItem(KEY);
    }

    window.RecentItems = { record, list, clear };
})();
