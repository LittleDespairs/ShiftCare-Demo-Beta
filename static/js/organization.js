(function () {
    const state = {
        user: null,
        organizationId: null,
        organizationName: "",
        membership: null,
        employees: [],
        clientConfig: null,
    };

    const elements = {};
    const INVITATION_ROLES = new Set(["owner", "admin"]);
    const MEMBER_VIEW_ROLES = new Set(["owner", "admin", "scheduler", "manager"]);

    function text(value) {
        return window.escapeHtml ? window.escapeHtml(value) : String(value ?? "");
    }

    function uiText(key, fallback) {
        if (typeof window.organizationAuthText === "function") {
            const translated = window.organizationAuthText(key);
            return translated === key ? (fallback || key) : translated;
        }
        return fallback || key;
    }

    async function confirmAction(message) {
        if (typeof window.appConfirm === "function") {
            return window.appConfirm(text(message), {
                confirmText: uiText("common_delete", "Delete"),
                html: true,
            });
        }
        return window.confirm(message);
    }

    function setMessage(value, type = "") {
        elements.message.textContent = value || "";
        elements.message.className = `organization-message ${type}`.trim();
    }

    function setInviteResult(value) {
        elements.inviteResult.value = value || "";
        elements.inviteResultWrap.hidden = !value;
    }

    function configuredPublicBaseUrl() {
        return String(state.clientConfig?.public_app_base_url || "").replace(/\/+$/, "");
    }

    function employeePortalUrl() {
        const configuredUrl = String(state.clientConfig?.employee_portal_url || "").trim();
        if (configuredUrl) return configuredUrl;
        const publicBaseUrl = configuredPublicBaseUrl();
        return `${publicBaseUrl || window.location.origin}/login`;
    }

    function invitationUrlFromResponse(response) {
        if (response.invitation_url) return response.invitation_url;
        const token = response.invitation_token || "";
        const publicBaseUrl = configuredPublicBaseUrl();
        return `${publicBaseUrl || window.location.origin}/accept-invitation?token=${encodeURIComponent(token)}`;
    }

    function activeMemberships() {
        return (state.user?.memberships || []).filter((membership) => membership.status === "active");
    }

    function canManageInvitations() {
        return INVITATION_ROLES.has(state.membership?.role);
    }

    function canViewMembers() {
        return MEMBER_VIEW_ROLES.has(state.membership?.role);
    }

    function selectMembership() {
        const membership = window.scheduleAuth.getActiveMembership(state.user);
        state.membership = membership;
        state.organizationId = membership?.organization_id || null;
        state.organizationName = membership?.organization_name || "";
        if (state.organizationId) {
            window.scheduleAuth.setActiveOrganizationId(state.organizationId);
        }
    }

    async function refreshCurrentUser() {
        const response = await window.scheduleAuth.request("/api/auth/me");
        window.scheduleAuth.setSession({
            access_token: window.scheduleAuth.getToken(),
            user: response.user,
        });
        state.user = response.user;
        selectMembership();
    }

    function renderOrganizationSelector() {
        const memberships = activeMemberships();
        elements.organizationSelectorWrap.hidden = memberships.length <= 1;
        elements.organizationSelect.innerHTML = memberships.map((membership) => `
            <option value="${membership.organization_id}" ${membership.organization_id === state.organizationId ? "selected" : ""}>
                ${text(membership.organization_name)}
            </option>
        `).join("");
    }

    function renderIdentity() {
        elements.identity.innerHTML = `
            <strong>${text(state.user.full_name)}</strong>
            <span>${text(state.user.email)}</span>
            <span>${text(state.membership?.organization_name || "No organization")} · ${text(state.membership?.role || "no role")}</span>
        `;
        elements.title.textContent = state.organizationName || "Organization";
        elements.profileName.value = state.user.full_name || "";
        elements.profileEmail.value = state.user.email || "";
    }

    function renderEmployeePortal() {
        if (!elements.employeePortalUrl) return;
        elements.employeePortalUrl.value = employeePortalUrl();
    }

    function renderPermissions() {
        elements.inviteForm.hidden = !canManageInvitations();
        if (!canManageInvitations()) {
            setInviteResult("");
            renderInvitations([], "Only owners and admins can manage invitations.");
        }
        if (!canViewMembers()) {
            renderMembers([], "Your role does not allow viewing the member list.");
        }
    }

    function renderMembers(members, emptyMessage = "No members found.") {
        if (!members.length) {
            elements.membersBody.innerHTML = `<tr><td colspan="6">${text(emptyMessage)}</td></tr>`;
            return;
        }
        elements.membersBody.innerHTML = members.map((member) => `
            <tr>
                <td>${text(member.full_name)}</td>
                <td>${text(member.email)}</td>
                <td>${text(member.employee_name || "")}</td>
                <td>${text(member.role)}</td>
                <td>${text(member.membership_status)}</td>
                <td>${member.email_verified ? "Yes" : "No"}</td>
                <td>
                    <div class="organization-table-actions">
                        <button
                            class="organization-table-button danger"
                            data-organization-action="remove-member"
                            data-user-id="${Number(member.user_id)}"
                            data-linked-employee-id="${Number(member.employee_id || 0)}"
                            ${member.user_id === state.user.id || member.membership_status !== "active" ? "disabled" : ""}
                            type="button"
                        >
                            ${text(uiText("org_remove_member", "Remove"))}
                        </button>
                    </div>
                </td>
            </tr>
        `).join("");
    }

    function renderInvitations(invitations, emptyMessage = "No invitations found.") {
        if (!invitations.length) {
            elements.invitationsBody.innerHTML = `<tr><td colspan="7">${text(emptyMessage)}</td></tr>`;
            return;
        }
        elements.invitationsBody.innerHTML = invitations.map((invitation) => `
            <tr>
                <td>${text(invitation.email)}</td>
                <td>${text(invitation.employee_name || "")}</td>
                <td>${text(invitation.role)}</td>
                <td>${text(invitation.status)}</td>
                <td>${text(invitation.expires_at)}</td>
                <td>${text(invitation.accepted_at || "")}</td>
                <td>
                    <div class="organization-table-actions">
                        <button
                            class="organization-table-button danger"
                            data-organization-action="revoke-invitation"
                            data-invitation-id="${Number(invitation.id)}"
                            data-pending-employee-id="${Number(invitation.employee_id || 0)}"
                            ${invitation.status !== "pending" ? "disabled" : ""}
                            type="button"
                        >
                            ${text(uiText("org_revoke_invitation", "Revoke"))}
                        </button>
                        <button
                            class="organization-table-button"
                            data-organization-action="regenerate-invitation"
                            data-invitation-id="${Number(invitation.id)}"
                            ${invitation.status !== "pending" ? "disabled" : ""}
                            type="button"
                        >
                            ${text(uiText("org_regenerate_invitation", "New link"))}
                        </button>
                    </div>
                </td>
            </tr>
        `).join("");
    }

    async function removeMember(userId) {
        const confirmed = await confirmAction(uiText("org_msg_confirm_remove_member", "Remove this member from the organization?"));
        if (!confirmed) return;
        setMessage("", "");
        try {
            await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/members/${userId}`, {
                method: "DELETE",
            });
            await refreshCurrentUser();
            renderOrganizationSelector();
            renderIdentity();
            renderPermissions();
            await loadOrganizationData();
            renderEmployeeSelector();
            setMessage(uiText("org_msg_member_removed", "Member access removed."), "success");
        } catch (error) {
            setMessage(error.message, "error");
        }
    }

    async function revokeInvitation(invitationId) {
        const confirmed = await confirmAction(uiText("org_msg_confirm_revoke_invitation", "Revoke this invitation link?"));
        if (!confirmed) return;
        setMessage("", "");
        try {
            await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/invitations/${invitationId}`, {
                method: "DELETE",
            });
            await loadOrganizationData();
            renderEmployeeSelector();
            setMessage(uiText("org_msg_invitation_revoked", "Invitation revoked."), "success");
        } catch (error) {
            setMessage(error.message, "error");
        }
    }

    async function regenerateInvitation(invitationId) {
        setInviteResult("");
        setMessage("", "");
        try {
            const response = await window.scheduleAuth.request(
                `/api/organizations/${state.organizationId}/invitations/${invitationId}/regenerate-token`,
                { method: "POST" },
            );
            setInviteResult(invitationUrlFromResponse(response));
            await loadOrganizationData();
            renderEmployeeSelector();
            setMessage(uiText("org_msg_invitation_link_generated", "Invitation link generated."), "success");
        } catch (error) {
            setMessage(error.message, "error");
        }
    }

    async function loadOrganizationData() {
        if (!state.organizationId) {
            setMessage("Current user has no active organization.", "error");
            return;
        }

        const requests = [];
        if (canViewMembers()) {
            requests.push(window.scheduleAuth.request(`/api/organizations/${state.organizationId}/members`));
        }
        if (canManageInvitations()) {
            requests.push(window.scheduleAuth.request(`/api/organizations/${state.organizationId}/invitations`));
        }

        const responses = await Promise.all(requests);
        let responseIndex = 0;
        if (canViewMembers()) {
            renderMembers(responses[responseIndex].members || []);
            responseIndex += 1;
        }
        if (canManageInvitations()) {
            renderInvitations(responses[responseIndex].invitations || []);
        }
    }

    async function loadEmployeesForInvitations() {
        if (!canManageInvitations()) {
            state.employees = [];
            renderEmployeeSelector();
            return;
        }
        try {
            state.employees = await window.scheduleAuth.request("/api/employees");
            renderEmployeeSelector();
        } catch (error) {
            state.employees = [];
            renderEmployeeSelector();
            setMessage(error.message, "error");
        }
    }

    function linkedEmployeeIds() {
        const ids = new Set();
        elements.membersBody.querySelectorAll("[data-linked-employee-id]").forEach((element) => {
            const employeeId = Number(element.dataset.linkedEmployeeId);
            if (employeeId) ids.add(employeeId);
        });
        elements.invitationsBody.querySelectorAll("[data-pending-employee-id]").forEach((element) => {
            if (element.disabled) return;
            const employeeId = Number(element.dataset.pendingEmployeeId);
            if (employeeId) ids.add(employeeId);
        });
        return ids;
    }

    function renderEmployeeSelector() {
        if (!elements.inviteEmployee) return;
        const linkedIds = linkedEmployeeIds();
        const currentValue = elements.inviteEmployee.value;
        const employeeLinkEnabled = elements.inviteRole?.value === "employee";
        elements.inviteEmployee.innerHTML = [
            `<option value="">${text(uiText("org_no_employee_link", "No employee link"))}</option>`,
            ...state.employees.map((employee) => {
                const disabled = linkedIds.has(Number(employee.id)) ? "disabled" : "";
                const selected = String(employee.id) === currentValue ? "selected" : "";
                return `<option value="${Number(employee.id)}" ${disabled} ${selected}>${text(employee.full_name)}</option>`;
            }),
        ].join("");
        elements.inviteEmployee.disabled = !employeeLinkEnabled;
        if (!employeeLinkEnabled) {
            elements.inviteEmployee.value = "";
        }
    }

    function bindInviteForm() {
        elements.inviteForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!canManageInvitations()) return;
            setInviteResult("");
            setMessage("Creating invitation...", "");
            try {
                const response = await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/invitations`, {
                    method: "POST",
                    body: JSON.stringify({
                        email: elements.inviteEmail.value,
                        employee_id: elements.inviteEmployee.value ? Number(elements.inviteEmployee.value) : null,
                        role: elements.inviteRole.value,
                        expires_in_days: Number(elements.inviteDays.value),
                    }),
                });
                setInviteResult(invitationUrlFromResponse(response));
                elements.inviteForm.reset();
                elements.inviteDays.value = "7";
                await loadOrganizationData();
                renderEmployeeSelector();
                setMessage("Invitation created.", "success");
            } catch (error) {
                setMessage(error.message, "error");
            }
        });
    }

    function bindProfileForms() {
        elements.profileForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            setMessage("Saving profile...", "");
            try {
                const response = await window.scheduleAuth.request("/api/auth/profile", {
                    method: "PUT",
                    body: JSON.stringify({ full_name: elements.profileName.value }),
                });
                window.scheduleAuth.setSession({
                    access_token: window.scheduleAuth.getToken(),
                    user: response.user,
                });
                state.user = response.user;
                selectMembership();
                renderOrganizationSelector();
                renderIdentity();
                setMessage("Profile saved.", "success");
            } catch (error) {
                setMessage(error.message, "error");
            }
        });

        elements.passwordForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            setMessage("Changing password...", "");
            try {
                await window.scheduleAuth.request("/api/auth/change-password", {
                    method: "POST",
                    body: JSON.stringify({
                        current_password: elements.currentPassword.value,
                        new_password: elements.newPassword.value,
                    }),
                });
                elements.passwordForm.reset();
                setMessage("Password changed.", "success");
            } catch (error) {
                setMessage(error.message, "error");
            }
        });
    }

    function normalizeCloudApiBaseUrl(value) {
        const normalized = window.scheduleAuth.setApiBaseUrl(value);
        window.scheduleAuth.useLocalApi();
        return normalized;
    }

    function setCloudStatus(value, type = "") {
        if (!elements.cloudLinkStatus) return;
        elements.cloudLinkStatus.textContent = value || "";
        elements.cloudLinkStatus.className = `organization-message ${type}`.trim();
    }

    async function cloudRequest(baseUrl, path, options = {}, token = "") {
        const headers = new Headers(options.headers || {});
        if (token) headers.set("Authorization", `Bearer ${token}`);
        if (options.body && !headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }
        const response = await window.scheduleAuth.nativeFetch(`${baseUrl}${path}`, { ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || `Cloud request failed with ${response.status}`);
        }
        return data;
    }

    function getCloudMembership(cloudUser) {
        const memberships = (cloudUser?.memberships || []).filter((membership) => membership.status === "active");
        const preferred = memberships.find((membership) => membership.role === "owner" || membership.role === "admin");
        return preferred || memberships[0] || null;
    }

    async function loginOrBootstrapCloud(baseUrl) {
        const email = elements.cloudEmail.value.trim();
        const password = elements.cloudPassword.value;
        try {
            return await cloudRequest(baseUrl, "/api/auth/login", {
                method: "POST",
                body: JSON.stringify({ email, password }),
            });
        } catch (loginError) {
            const status = await cloudRequest(baseUrl, "/api/auth/status");
            if (!status.bootstrap_available) {
                throw loginError;
            }
            return cloudRequest(baseUrl, "/api/auth/bootstrap", {
                method: "POST",
                body: JSON.stringify({
                    organization_name: state.organizationName || "ShiftCare Organization",
                    full_name: state.user.full_name || "Organization Owner",
                    email,
                    password,
                }),
            });
        }
    }

    async function uploadAndLinkCloudOrganization() {
        if (!canManageInvitations()) {
            setCloudStatus("Only owners and admins can connect this organization to cloud.", "error");
            return;
        }
        const cloudBaseUrl = normalizeCloudApiBaseUrl(elements.cloudApiBaseUrl.value);
        if (!cloudBaseUrl) {
            setCloudStatus("Enter a valid Cloud API URL.", "error");
            return;
        }
        setMessage("", "");
        setCloudStatus("Preparing local organization export...", "");
        try {
            const localBundle = await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/cloud-export`);
            setCloudStatus("Signing in to Cloud beta API...", "");
            const cloudSession = await loginOrBootstrapCloud(cloudBaseUrl);
            const cloudMembership = getCloudMembership(cloudSession.user);
            if (!cloudMembership || !["owner", "admin"].includes(cloudMembership.role)) {
                throw new Error("Cloud account must be an owner or admin of the target organization.");
            }
            setCloudStatus("Uploading local organization to cloud...", "");
            const importResponse = await cloudRequest(
                cloudBaseUrl,
                `/api/organizations/${cloudMembership.organization_id}/cloud-import`,
                {
                    method: "POST",
                    body: JSON.stringify({
                        bundle: localBundle,
                        replace_existing: elements.cloudReplaceExisting.checked,
                    }),
                },
                cloudSession.access_token,
            );
            setCloudStatus("Saving cloud link locally...", "");
            await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/cloud-link`, {
                method: "POST",
                body: JSON.stringify({
                    cloud_api_base_url: cloudBaseUrl,
                    cloud_organization_id: cloudMembership.organization_id,
                    cloud_organization_public_id: importResponse.organization_public_id || cloudMembership.organization_public_id,
                    linked_at: new Date().toISOString(),
                }),
            });
            setCloudStatus(
                `Linked. Imported ${importResponse.imported.employees} employees, ${importResponse.imported.positions} positions, ${importResponse.imported.shift_templates} shift templates.`,
                "success",
            );
            elements.cloudPassword.value = "";
        } catch (error) {
            setCloudStatus(error.message, "error");
        }
    }

    function bindActions() {
        elements.organizationSelect.addEventListener("change", async () => {
            window.scheduleAuth.setActiveOrganizationId(Number(elements.organizationSelect.value));
            selectMembership();
            renderIdentity();
            renderPermissions();
            setMessage("", "");
            try {
                await loadOrganizationData();
                await loadEmployeesForInvitations();
            } catch (error) {
                setMessage(error.message, "error");
            }
        });
        elements.copyInvite.addEventListener("click", async () => {
            if (!elements.inviteResult.value) return;
            await navigator.clipboard.writeText(elements.inviteResult.value);
            setMessage("Invitation link copied.", "success");
        });
        elements.copyEmployeePortal?.addEventListener("click", async () => {
            if (!elements.employeePortalUrl.value) return;
            await navigator.clipboard.writeText(elements.employeePortalUrl.value);
            setMessage(uiText("org_msg_employee_portal_copied", "Employee portal link copied."), "success");
        });
        elements.cloudLinkForm?.addEventListener("submit", async (event) => {
            event.preventDefault();
            await uploadAndLinkCloudOrganization();
        });
        elements.inviteRole.addEventListener("change", renderEmployeeSelector);
        elements.membersBody.addEventListener("click", (event) => {
            const button = event.target.closest('[data-organization-action="remove-member"]');
            if (!button || button.disabled) return;
            removeMember(Number(button.dataset.userId));
        });
        elements.invitationsBody.addEventListener("click", (event) => {
            const revokeButton = event.target.closest('[data-organization-action="revoke-invitation"]');
            if (revokeButton && !revokeButton.disabled) {
                revokeInvitation(Number(revokeButton.dataset.invitationId));
                return;
            }
            const button = event.target.closest('[data-organization-action="regenerate-invitation"]');
            if (!button || button.disabled) return;
            regenerateInvitation(Number(button.dataset.invitationId));
        });
        elements.logout.addEventListener("click", async () => {
            try {
                await window.scheduleAuth.request("/api/auth/logout", { method: "POST" });
            } catch (error) {
                // Local session is cleared regardless of server response.
            }
            window.scheduleAuth.clearSession();
            window.location.href = "/login";
        });
    }

    document.addEventListener("DOMContentLoaded", async () => {
        Object.assign(elements, {
            title: document.getElementById("organization-title"),
            identity: document.getElementById("organization-identity"),
            message: document.getElementById("organization-message"),
            organizationSelectorWrap: document.getElementById("organization-selector-wrap"),
            organizationSelect: document.getElementById("organization-select"),
            profileForm: document.getElementById("profile-form"),
            profileName: document.getElementById("profile-name"),
            profileEmail: document.getElementById("profile-email"),
            passwordForm: document.getElementById("password-form"),
            currentPassword: document.getElementById("current-password"),
            newPassword: document.getElementById("new-password"),
            membersBody: document.getElementById("members-table-body"),
            invitationsBody: document.getElementById("invitations-table-body"),
            inviteForm: document.getElementById("invite-form"),
            inviteEmployee: document.getElementById("invite-employee"),
            inviteEmail: document.getElementById("invite-email"),
            inviteRole: document.getElementById("invite-role"),
            inviteDays: document.getElementById("invite-days"),
        inviteResult: document.getElementById("invite-result"),
        inviteResultWrap: document.getElementById("invite-result-wrap"),
        copyInvite: document.getElementById("copy-invite-btn"),
        employeePortalUrl: document.getElementById("employee-portal-url"),
        copyEmployeePortal: document.getElementById("copy-employee-portal-btn"),
        cloudLinkForm: document.getElementById("cloud-link-form"),
        cloudApiBaseUrl: document.getElementById("cloud-api-base-url"),
        cloudEmail: document.getElementById("cloud-email"),
        cloudPassword: document.getElementById("cloud-password"),
        cloudReplaceExisting: document.getElementById("cloud-replace-existing"),
        cloudLinkStatus: document.getElementById("cloud-link-status"),
        logout: document.getElementById("logout-btn"),
    });

        state.user = window.scheduleAuth.requireSession();
        if (!state.user) return;
        bindInviteForm();
        bindProfileForms();
        bindActions();
        try {
            state.clientConfig = await window.scheduleAuth.request("/api/client-config");
            if (elements.cloudApiBaseUrl) {
                elements.cloudApiBaseUrl.value = state.clientConfig.default_api_base_url || window.scheduleAuth.CLOUD_API_BASE_URL;
            }
            await refreshCurrentUser();
            renderOrganizationSelector();
            renderIdentity();
            renderEmployeePortal();
            renderPermissions();
            await loadOrganizationData();
            await loadEmployeesForInvitations();
        } catch (error) {
            setMessage(error.message, "error");
        }
    });
})();
