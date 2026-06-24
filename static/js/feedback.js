(function () {
    const elements = {
        form: document.getElementById("feedback-form"),
        type: document.getElementById("feedback-type"),
        severity: document.getElementById("feedback-severity"),
        area: document.getElementById("feedback-area"),
        contact: document.getElementById("feedback-contact"),
        title: document.getElementById("feedback-title"),
        description: document.getElementById("feedback-description"),
        steps: document.getElementById("feedback-steps"),
        actual: document.getElementById("feedback-actual"),
        expected: document.getElementById("feedback-expected"),
        submit: document.getElementById("feedback-submit"),
        message: document.getElementById("feedback-message"),
    };

    function setMessage(text, type) {
        if (!elements.message) return;
        elements.message.textContent = text || "";
        elements.message.className = `organization-message ${type || ""}`.trim();
    }

    function valueOrNull(element) {
        const value = String(element?.value || "").trim();
        return value || null;
    }

    function activeUser() {
        return window.scheduleAuth?.requireSession?.() || null;
    }

    function activeMembership() {
        return window.scheduleAuth?.getActiveMembership?.() || null;
    }

    function updateBugFields() {
        const isBug = elements.type?.value === "bug";
        document.querySelectorAll(".feedback-bug-field").forEach((field) => {
            field.hidden = !isBug;
        });
    }

    function buildClientContext() {
        return {
            app_name: document.body?.dataset?.appName || "",
            page_url: window.location.href,
            referrer: document.referrer || "",
            user_agent: window.navigator.userAgent,
            language: window.navigator.language,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight,
                device_pixel_ratio: window.devicePixelRatio || 1,
            },
            online: window.navigator.onLine,
            api_mode: window.scheduleAuth?.getApiModePreference?.() || "",
            api_base_url: window.scheduleAuth?.getApiBaseUrl?.() || "",
            frontend_errors: window.scheduleAuth?.getFrontendErrors?.() || [],
        };
    }

    function buildPayload() {
        const membership = activeMembership();
        return {
            report_type: elements.type.value,
            severity: elements.severity.value,
            area: elements.area.value,
            title: valueOrNull(elements.title),
            description: valueOrNull(elements.description),
            steps_to_reproduce: elements.type.value === "bug" ? valueOrNull(elements.steps) : null,
            actual_result: elements.type.value === "bug" ? valueOrNull(elements.actual) : null,
            expected_result: elements.type.value === "bug" ? valueOrNull(elements.expected) : null,
            contact_email: valueOrNull(elements.contact),
            organization_id: membership?.organization_id || null,
            page_url: window.location.href,
            client_context: buildClientContext(),
        };
    }

    function validatePayload(payload) {
        if (!payload.title || payload.title.length < 3) {
            return "Title must contain at least 3 characters.";
        }
        if (!payload.description || payload.description.length < 10) {
            return "Description must contain at least 10 characters.";
        }
        return "";
    }

    async function submitFeedback(event) {
        event.preventDefault();
        const payload = buildPayload();
        const validationError = validatePayload(payload);
        if (validationError) {
            setMessage(validationError, "error");
            return;
        }

        elements.submit.disabled = true;
        setMessage("Submitting report...", "");
        try {
            const result = await window.scheduleAuth.request("/api/feedback/reports", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            const notificationStatus = result.notification?.status || "not_attempted";
            if (notificationStatus === "sent" || notificationStatus === "forwarded") {
                setMessage(`Report submitted. Reference: ${result.report?.public_id || "-"}.`, "success");
            } else {
                setMessage(`Report saved. Reference: ${result.report?.public_id || "-"}.`, "success");
            }
            elements.form.reset();
            const user = window.scheduleAuth?.getUser?.();
            if (elements.contact && user?.email) {
                elements.contact.value = user.email;
            }
            updateBugFields();
        } catch (error) {
            setMessage(error.message || "Could not submit report.", "error");
        } finally {
            elements.submit.disabled = false;
        }
    }

    const user = activeUser();
    if (elements.contact && user?.email) {
        elements.contact.value = user.email;
    }
    elements.type?.addEventListener("change", updateBugFields);
    elements.form?.addEventListener("submit", submitFeedback);
    updateBugFields();
})();
