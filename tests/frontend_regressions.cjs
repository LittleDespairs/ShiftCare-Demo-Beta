const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { test } = require("node:test");

const formScript = fs.readFileSync("static/js/portal_settings.js", "utf8");
function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}
function portal(fetch) {
    function element() {
        return {
            disabled: false, checked: false, attributes: {}, listeners: {}, children: [],
            setAttribute(name, value) { this.attributes[name] = value; },
            replaceChildren(...children) { this.children = children; },
            addEventListener(name, callback) { this.listeners[name] = callback; }
        };
    }
    const ids = ["employee-portal-settings-form", "employee-portal-settings-fields", "employee_shift_swap_requests_enabled", "reload-employee-portal-settings-btn", "employee-portal-settings-message-box"];
    const elements = Object.fromEntries(ids.map(id => [id, element()]));
    const [form, fields, checkbox, retry, messages] = ids.map(id => elements[id]);
    let init;
    const document = { getElementById: id => elements[id], createElement: element, addEventListener(name, callback) { init = callback; } };
    vm.runInNewContext(formScript, { document, window: {}, fetch, TypeError });
    init();
    return { form, fields, checkbox, retry, messages, submit: () => form.listeners.submit({ preventDefault() {} }) };
}
const tick = () => new Promise(resolve => setImmediate(resolve));
const response = (body, ok = true) => ({ ok, json: async () => body });

test("portal cannot save before load and sends the intended flag once", async () => {
    const get = deferred(), put = deferred(), calls = [];
    const ui = portal((url, options) => { calls.push(options); return options.method ? put.promise : get.promise; });
    assert.equal(ui.fields.disabled, true);
    await ui.submit();
    assert.equal(calls.length, 1);
    get.resolve(response({ employee_shift_swap_requests_enabled: true }));
    await tick();
    assert.equal(ui.checkbox.checked, true);
    assert.equal(ui.fields.disabled, false);
    ui.checkbox.checked = false;
    const saving = ui.submit();
    await ui.submit();
    assert.equal(calls.length, 2);
    assert.equal(JSON.parse(calls[1].body).employee_shift_swap_requests_enabled, false);
    assert.equal(ui.fields.disabled, true);
    put.resolve(response({ settings: { employee_shift_swap_requests_enabled: false } }));
    await saving;
    assert.equal(ui.fields.disabled, false);
    assert.equal(ui.messages.children[0].className, "alert alert-success");
});

test("failed load remains disabled and can be retried", async () => {
    let attempts = 0;
    const ui = portal(async () => {
        if (++attempts === 1) throw new TypeError("offline");
        return response({ employee_shift_swap_requests_enabled: false });
    });
    await tick();
    assert.equal(ui.fields.disabled, true);
    assert.equal(ui.retry.disabled, false);
    assert.equal(ui.messages.children[0].className, "alert alert-danger");
    await ui.submit();
    assert.equal(attempts, 1);
    await ui.retry.listeners.click();
    assert.equal(ui.fields.disabled, false);
    assert.equal(ui.checkbox.checked, false);
});

test("save failures display feedback and re-enable retry without changing the chosen flag", async () => {
    for (const badResponse of [
        () => Promise.reject(new TypeError("offline")),
        async () => ({ ok: false, json: async () => { throw new SyntaxError("HTML gateway error"); } }),
        async () => response({ detail: "Forbidden" }, false),
        async () => response({ settings: {} })
    ]) {
        const active = portal((url, options) => options.method ? badResponse() : Promise.resolve(response({ employee_shift_swap_requests_enabled: true })));
        await tick();
        active.checkbox.checked = false;
        await active.submit();
        assert.equal(active.fields.disabled, false);
        assert.equal(active.checkbox.checked, false);
        assert.equal(active.messages.children[0].className, "alert alert-danger");
        assert.ok(active.messages.children[0].textContent.length > 0);
    }
});

test("service worker preserves other applications' caches and never caches failed responses", async () => {
    const listeners = {}, deleted = [], stored = [], lifetime = [];
    const cache = { put: async (...args) => stored.push(args), addAll: async () => {} };
    const caches = { open: async () => cache, keys: async () => ["other-app-cache", "shiftcare-old", "shiftcare-0.21.1_beta"], delete: async key => deleted.push(key), match: async () => undefined };
    const self = { location: { origin: "https://shiftcare.test" }, addEventListener: (name, fn) => { listeners[name] = fn; }, clients: { claim() {} }, skipWaiting() {} };
    const failure = { ok: false, status: 503 };
    vm.runInNewContext(fs.readFileSync("static/service-worker.js", "utf8"), { self, caches, URL, fetch: async () => failure });
    listeners.activate({ waitUntil: promise => lifetime.push(promise) });
    await Promise.all(lifetime);
    assert.deepEqual(deleted, ["shiftcare-old"]);
    let result;
    listeners.fetch({ request: { url: "https://shiftcare.test/static/js/i18n.js", method: "GET", mode: "cors" }, respondWith: p => { result = p; }, waitUntil: p => lifetime.push(p) });
    assert.equal(await result, failure);
    assert.equal(stored.length, 0);
    for (const url of ["https://shiftcare.test/api/app-settings", "https://another.test/static/js/script.js"]) {
        listeners.fetch({ request: { url, method: "GET" }, respondWith() { throw new Error("Must bypass service worker"); } });
    }
});

test("service worker installs on desktop and cloud when optional pages return 404", async () => {
    const desktopOnly = new Set(["/settings", "/employees", "/departments", "/positions", "/employee-positions", "/shift-templates", "/coverage-requirements"]);
    for (const cloud of [false, true]) {
        const stored = new Set(), listeners = {};
        const fetch = async url => ({ ok: url !== "/support" && !(cloud && desktopOnly.has(url)) });
        const cache = {
            async addAll(urls) {
                for (const url of urls) {
                    if (!(await fetch(url)).ok) throw new Error(`Required precache URL failed: ${url}`);
                    stored.add(url);
                }
            },
            async put(url) { stored.add(url); }
        };
        const self = { addEventListener: (name, callback) => { listeners[name] = callback; }, skipWaiting() {} };
        vm.runInNewContext(fs.readFileSync("static/service-worker.js", "utf8"), { self, caches: { open: async () => cache }, fetch });
        let installation;
        listeners.install({ waitUntil: promise => { installation = promise; } });
        await installation;
        assert.equal(stored.has("/login"), true);
        assert.equal(stored.has("/schedule"), true);
        assert.equal(stored.has("/settings"), !cloud);
        assert.equal(stored.has("/support"), false);
    }
});

function initialCloudLink({ protocol = 2, importError = null } = {}) {
    const calls = [], notices = [];
    const local = { format: "shiftcare.organization.v1", records: {} };
    const accepted = { sync_revision: "accepted-cloud-revision", records: {} };
    const source = fs.readFileSync("static/js/organization.js", "utf8");
    const start = source.indexOf("    async function uploadAndLinkCloudOrganization()");
    const end = source.indexOf("    async function unlinkCloudOrganization()", start);
    const submit = { disabled: false };
    const context = {
        cloudLinkBusy: false,
        canManageInvitations: () => true,
        normalizeCloudApiBaseUrl: value => value,
        uiText: (key, fallback) => fallback,
        setMessage() {},
        setCloudStatus: (...args) => notices.push(args),
        state: { organizationId: 1 },
        elements: { cloudApiBaseUrl: { value: "https://cloud.example.test" }, cloudPassword: { value: "test" }, cloudLinkForm: { querySelector: () => submit } },
        loginOrBootstrapCloud: async () => ({ user: {}, access_token: "fixture-cloud-token" }),
        getCloudMembership: () => ({ organization_id: 5, organization_public_id: "org-remote", role: "owner" }),
        loadCloudLinkStatus: async () => {},
        window: { scheduleAuth: { request: async (url, options) => {
            calls.push({ side: "local", url, options });
            return url.endsWith("cloud-export") ? local : { sync_pending: true };
        } } },
        cloudRequest: async (base, url, options, token) => {
            calls.push({ side: "cloud", url, options, token });
            if (url.endsWith("cloud-export")) return { sync_protocol: protocol, sync_revision: "observed-cloud-revision" };
            if (importError) throw new Error(importError);
            return { sync_bundle: accepted, imported: { employees: 2 } };
        }
    };
    const run = vm.runInNewContext(source.slice(start, end) + ";uploadAndLinkCloudOrganization", context);
    return { run, calls, notices, submit, accepted };
}

test("initial link uses remote CAS and forwards accepted baseline/token to local finalization", async () => {
    const link = initialCloudLink();
    await link.run();
    const posted = JSON.parse(link.calls.find(call => call.side === "cloud" && call.url.endsWith("cloud-import")).options.body);
    assert.deepEqual(posted.bundle.sync, { protocol: 2, base_revision: "observed-cloud-revision", initial_link: true });
    const finalized = JSON.parse(link.calls.find(call => call.side === "local" && call.url.endsWith("cloud-link")).options.body);
    assert.deepEqual(finalized.sync_bundle, link.accepted);
    assert.equal(finalized.cloud_access_token, "fixture-cloud-token");
    assert.match(link.notices.at(-1)[0], /waiting to synchronize/);
    assert.equal(link.submit.disabled, false);
});

test("initial link never finalizes an incompatible cloud or a conflicting import", async () => {
    for (const scenario of [{ protocol: 1 }, { importError: "Review required: populated cloud organization" }]) {
        const link = initialCloudLink(scenario);
        await link.run();
        assert.equal(link.calls.some(call => call.url.endsWith("cloud-link")), false);
        assert.equal(link.notices.at(-1)[1], "error");
        assert.equal(link.submit.disabled, false);
    }
});
