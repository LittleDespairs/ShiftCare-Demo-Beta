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

function weeklyPreferences(request) {
    const source = fs.readFileSync("templates/weekly_preferences.html", "utf8");
    function definition(name, nextName) {
        const declaration = source.indexOf(`function ${name}(`);
        const start = source.slice(declaration - 6, declaration) === "async " ? declaration - 6 : declaration;
        const next = source.indexOf(`function ${nextName}(`, start);
        const end = source.slice(next - 6, next) === "async " ? next - 6 : next;
        assert.ok(start >= 0 && end > start, `Missing weekly preference handler: ${name}`);
        return source.slice(start, end);
    }
    const calls = [], notices = [];
    const modalElement = () => ({ classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {} });
    const typeButtons = ["request_shift", "exclude_shift", "day_off", "vacation"].map(requestType => ({
        ...modalElement(), dataset: { requestType }
    }));
    const categoryButtons = ["morning", "evening", "night"].map(requestCategory => ({
        ...modalElement(), dataset: { requestCategory }
    }));
    const elements = {
        week_start: { value: "2026-09-13" },
        request_type_select: { value: "request_shift" },
        request_category_select: { value: "morning" },
        "request-modal-overlay": modalElement(),
        "request-category-field": { hidden: false }
    };
    const context = {
        document: {
            getElementById: id => elements[id],
            querySelectorAll: selector => selector === "[data-request-type]" ? typeButtons : categoryButtons
        },
        console: { error() {} },
        buildWeek: date => [date],
        isEmployeePortalPreferencesMode: () => false,
        normalizeRequest: item => item,
        preferenceKey: (id, date) => `${id}:${date}`,
        rebuildPreferenceRequestMap() {}, renderTable() {}, renderApprovalPanel() {},
        closeRequestModal() { context.pendingRequestTarget = null; },
        t: (key, fallback) => fallback,
        escapeHtml: value => String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"),
        showMessage: (text, type) => notices.push({ text, type }),
        preferencesMap: { previous: [] }, preferenceRequests: [{ id: 8, status: "pending" }],
        preferencesLoaded: true, weekDates: ["2026-09-06"],
        pendingRequestTarget: { employeeId: 5, date: "2026-09-13" },
        window: { scheduleAuth: { request: async (url, options = {}) => {
            calls.push({ url, options });
            return request(url, options);
        } } }
    };
    vm.createContext(context);
    vm.runInContext([
        definition("loadWeekPreferences", "handlePreferencesContextChanged"),
        definition("openRequestModal", "savePendingRequest"),
        definition("savePendingRequest", "decidePreferenceRequest"),
        definition("decidePreferenceRequest", "deletePreferenceRequest"),
        definition("deletePreferenceRequest", "deletePreference")
    ].join("\n"), context);
    return { context, calls, notices, elements };
}

test("weekly preference load preserves the server's sync conflict detail", async () => {
    const detail = "Sync needs review: these different copies have no agreed baseline; changes were preserved";
    const ui = weeklyPreferences(async () => { throw new Error(detail); });
    assert.equal(await ui.context.loadWeekPreferences(), false);
    assert.deepEqual(ui.notices, [{ text: detail, type: "danger" }]);
    assert.equal(ui.calls.length, 1);
    assert.deepEqual(ui.context.weekDates, ["2026-09-06"]);
});

test("failed approval-list load preserves displayed requests, reports failure and supports retry", async () => {
    let fail = true;
    const preference = { id: 4, employee_id: 5, preference_date: "2026-09-13", request_type: "request_shift" };
    const ui = weeklyPreferences(async url => {
        if (url.includes("preference-requests")) {
            if (fail) throw new Error("Approval list unavailable");
            return [];
        }
        return [preference];
    });
    assert.equal(await ui.context.loadWeekPreferences(), false);
    assert.equal(ui.context.preferenceRequests[0].id, 8);
    assert.ok("previous" in ui.context.preferencesMap);
    assert.deepEqual(ui.notices, [{ text: "Approval list unavailable", type: "danger" }]);
    fail = false;
    assert.equal(await ui.context.loadWeekPreferences(), true);
    assert.equal(ui.context.preferencesMap["5:2026-09-13"][0].id, 4);
    assert.equal(ui.context.preferenceRequests.length, 0);
    assert.equal(ui.notices.at(-1).type, "success");
});

test("saved preference, approval and deletion do not hide a failed reload with success", async () => {
    for (const action of ["savePendingRequest", "decidePreferenceRequest", "deletePreferenceRequest"]) {
        const ui = weeklyPreferences(async (url, options) => {
            if (options.method) return { status: "saved" };
            throw new Error("Sync needs review: <cloud> copies differ");
        });
        await ui.context[action](8, "approved");
        assert.ok(ui.calls[0].options.method);
        assert.equal(ui.notices.length, 1);
        assert.equal(ui.notices[0].type, "warning");
        assert.match(ui.notices[0].text, /change was saved/);
        assert.match(ui.notices[0].text, /Sync needs review: &lt;cloud&gt; copies differ/);
    }
});

test("malformed preference lists fail visibly and pending approval remains distinct from a saved preference", async () => {
    const broken = weeklyPreferences(async () => ({}));
    assert.equal(await broken.context.loadWeekPreferences(), false);
    assert.equal(broken.notices.at(-1).type, "danger");
    const pending = weeklyPreferences(async (url, options) => options.method ? { status: "pending_approval" } : []);
    await pending.context.savePendingRequest();
    assert.equal(pending.notices.at(-1).type, "info");
    assert.match(pending.notices.at(-1).text, /sent for administrator approval/);
});

test("weekly request modal resets to a morning shift and serializes the selected type/category", async () => {
    const ui = weeklyPreferences(async (url, options) => options.method ? { status: "saved" } : []);
    const choices = [
        ...["request_shift", "exclude_shift"].flatMap(type => ["morning", "evening", "night"].map(category => [type, category])),
        ["day_off", null], ["vacation", null]
    ];
    for (const [type, category] of choices) {
        ui.context.openRequestModal(5, "2026-09-15");
        assert.equal(ui.elements.request_type_select.value, "request_shift");
        assert.equal(ui.elements.request_category_select.value, "morning");
        ui.context.setRequestType(type);
        if (category) ui.context.setRequestCategory(category);
        assert.equal(ui.elements["request-category-field"].hidden, category === null);
        await ui.context.savePendingRequest();
        const write = ui.calls.filter(call => call.options.method === "POST").at(-1);
        assert.deepEqual(JSON.parse(write.options.body), {
            employee_id: 5, week_start_date: "2026-09-13", preference_date: "2026-09-15",
            request_type: type, target_category: category
        });
    }
    ui.context.openRequestModal(5, "2026-09-16");
    assert.equal(ui.elements.request_type_select.value, "request_shift", "Vacation must not persist as the next request's default");
    assert.equal(ui.elements.request_category_select.value, "morning");
});
