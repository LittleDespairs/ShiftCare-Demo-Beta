(function () {
    const state = {
        user: null,
        organizationId: null,
        organizationName: "",
        membership: null,
        members: [],
        invitations: [],
        employees: [],
        clientConfig: null,
        cloudLink: null,
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
        if (publicBaseUrl) return `${publicBaseUrl}/login`;
        return "";
    }

    function invitationUrlFromResponse(response) {
        if (response.invitation_url) return response.invitation_url;
        const token = response.invitation_token || "";
        const publicBaseUrl = configuredPublicBaseUrl();
        if (publicBaseUrl && token) {
            return `${publicBaseUrl}/accept-invitation?token=${encodeURIComponent(token)}`;
        }
        const cloudBaseUrl = window.scheduleAuth?.CLOUD_API_FALLBACK_BASE_URL || window.scheduleAuth?.CLOUD_API_BASE_URL || "";
        if (cloudBaseUrl && token) {
            return `${cloudBaseUrl.replace(/\/+$/, "")}/accept-invitation?token=${encodeURIComponent(token)}`;
        }
        throw new Error("Invitation link was not generated. Check cloud connection and try again.");
    }

    function activeMemberships() {
        return (state.user?.memberships || []).filter((membership) => membership.status === "active");
    }

    function canManageInvitations() {
        if (state.clientConfig?.cloud_employee_portal_mode) return false;
        return INVITATION_ROLES.has(state.membership?.role);
    }

    function canViewMembers() {
        if (state.clientConfig?.cloud_employee_portal_mode) return false;
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
        elements.employeePortalUrl.value = employeePortalUrl() || "Employee portal URL is not configured.";
        if (elements.copyEmployeePortal) {
            elements.copyEmployeePortal.disabled = !employeePortalUrl();
        }
    }

    function renderPermissions() {
        elements.inviteForm.hidden = !canManageInvitations();
        if (elements.employeePortalPanel) {
            elements.employeePortalPanel.hidden = Boolean(state.clientConfig?.cloud_employee_portal_mode);
        }
        if (elements.membersPanel) {
            elements.membersPanel.hidden = !canViewMembers();
        }
        if (elements.invitationsPanel) {
            elements.invitationsPanel.hidden = !canManageInvitations();
        }
        if (!canManageInvitations()) {
            setInviteResult("");
            renderInvitations([], "Only owners and admins can manage invitations.");
        }
        if (!canViewMembers()) {
            renderMembers([], "Your role does not allow viewing the member list.");
        }
    }

    function renderMembers(members, emptyMessage = "No members found.") {
        state.members = members;
        if (!members.length) {
            elements.membersBody.innerHTML = `<tr><td colspan="7">${text(emptyMessage)}</td></tr>`;
            return;
        }
        elements.membersBody.innerHTML = members.map((member) => `
            <tr>
                <td>${text(member.full_name)}</td>
                <td>${text(member.email)}</td>
                <td>${renderMemberEmployeeCell(member)}</td>
                <td>${text(member.role)}</td>
                <td>${text(member.membership_status)}</td>
                <td>${member.email_verified ? "Yes" : "No"}</td>
                <td>
                    <div class="organization-table-actions">
                        <button
                            class="organization-table-button danger"
                            data-organization-action="remove-member"
                            data-user-id="${Number(member.user_id)}"
                            data-linked-employee-id="${member.membership_status === "active" ? Number(member.employee_id || 0) : 0}"
                            data-linked-employee-public-id="${member.membership_status === "active" ? text(member.employee_public_id || "") : ""}"
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

    function renderMemberEmployeeCell(member) {
        if (member.role !== "employee") return "";
        return text(member.employee_name || uiText("org_member_employee_not_linked", "Not linked"));
    }

    function renderInvitations(invitations, emptyMessage = "No invitations found.") {
        state.invitations = invitations;
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
                            data-pending-employee-public-id="${text(invitation.employee_public_id || "")}"
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
            state.members = responses[responseIndex].members || [];
            renderMembers(state.members);
            responseIndex += 1;
        }
        if (canManageInvitations()) {
            state.invitations = responses[responseIndex].invitations || [];
            renderInvitations(state.invitations);
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
            renderMembers(state.members || []);
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

    function linkedEmployeePublicIds() {
        const ids = new Set();
        elements.membersBody.querySelectorAll("[data-linked-employee-public-id]").forEach((element) => {
            const employeePublicId = String(element.dataset.linkedEmployeePublicId || "").trim();
            if (employeePublicId) ids.add(employeePublicId);
        });
        elements.invitationsBody.querySelectorAll("[data-pending-employee-public-id]").forEach((element) => {
            if (element.disabled) return;
            const employeePublicId = String(element.dataset.pendingEmployeePublicId || "").trim();
            if (employeePublicId) ids.add(employeePublicId);
        });
        return ids;
    }

    function renderEmployeeSelector() {
        if (!elements.inviteEmployee) return;
        const linkedIds = linkedEmployeeIds();
        const linkedPublicIds = linkedEmployeePublicIds();
        const currentValue = elements.inviteEmployee.value;
        elements.inviteEmployee.innerHTML = [
            `<option value="">${text(uiText("preferences_select_employee", "Select employee"))}</option>`,
            ...state.employees.map((employee) => {
                const disabled = linkedIds.has(Number(employee.id)) || linkedPublicIds.has(String(employee.public_id || "")) ? "disabled" : "";
                const selected = String(employee.id) === currentValue ? "selected" : "";
                return `<option value="${Number(employee.id)}" ${disabled} ${selected}>${text(employee.full_name)}</option>`;
            }),
        ].join("");
        elements.inviteEmployee.required = true;
    }

    function bindInviteForm() {
        elements.inviteForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!canManageInvitations()) return;
            setInviteResult("");
            setMessage("Creating invitation...", "");
            if (!elements.inviteEmployee.value) {
                setMessage("Select an employee before creating an employee invitation.", "error");
                elements.inviteEmployee.focus();
                return;
            }
            try {
                const response = await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/invitations`, {
                    method: "POST",
                    body: JSON.stringify({
                        email: elements.inviteEmail.value,
                        employee_id: Number(elements.inviteEmployee.value),
                        role: "employee",
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

    function renderCloudLinkSummary(link) {
        if (!elements.cloudLinkSummary) return;
        state.cloudLink = link?.linked ? link : null;
        elements.cloudLinkSummary.hidden = !state.cloudLink;
        if (elements.cloudUnlink) {
            elements.cloudUnlink.hidden = !state.cloudLink || !canManageInvitations();
        }
        renderEmployeePortal();
        if (!state.cloudLink) return;
        elements.cloudLinkApi.textContent = link.cloud_api_base_url || "-";
        elements.cloudLinkOrganization.textContent = link.cloud_organization_public_id
            ? `${link.cloud_organization_public_id} (#${link.cloud_organization_id})`
            : `#${link.cloud_organization_id}`;
        elements.cloudLinkTime.textContent = link.linked_at || "-";
        if (elements.cloudApiBaseUrl && link.cloud_api_base_url) {
            elements.cloudApiBaseUrl.value = link.cloud_api_base_url;
        }
    }

    async function loadCloudLinkStatus() {
        if (!state.organizationId || !canViewMembers()) return;
        try {
            const link = await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/cloud-link`);
            renderCloudLinkSummary(link);
            if (link.linked) {
                setCloudStatus(uiText("org_cloud_linked_status", "This installation is linked to cloud."), "success");
            } else {
                setCloudStatus("Cloud portal is optional and is not connected for this local organization.", "");
            }
        } catch (error) {
            renderCloudLinkSummary(null);
        }
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
            await loadCloudLinkStatus();
            elements.cloudPassword.value = "";
        } catch (error) {
            setCloudStatus(error.message, "error");
        }
    }

    async function unlinkCloudOrganization() {
        if (!canManageInvitations()) {
            setCloudStatus("Only owners and admins can disconnect the cloud portal.", "error");
            return;
        }
        setCloudStatus("Disconnecting cloud portal...", "");
        try {
            await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/cloud-link`, {
                method: "DELETE",
            });
            renderCloudLinkSummary(null);
            setCloudStatus("Cloud portal disconnected for this local organization.", "success");
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
                await loadCloudLinkStatus();
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
        elements.cloudUnlink?.addEventListener("click", unlinkCloudOrganization);
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
            employeePortalPanel: document.getElementById("employee-portal-panel"),
            membersPanel: document.getElementById("members-panel"),
            invitationsPanel: document.getElementById("invitations-panel"),
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
            cloudLinkSummary: document.getElementById("cloud-link-summary"),
            cloudLinkApi: document.getElementById("cloud-link-api"),
            cloudLinkOrganization: document.getElementById("cloud-link-organization"),
            cloudLinkTime: document.getElementById("cloud-link-time"),
            cloudLinkStatus: document.getElementById("cloud-link-status"),
            cloudUnlink: document.getElementById("cloud-unlink-btn"),
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
            await loadCloudLinkStatus();
        } catch (error) {
            setMessage(error.message, "error");
        }
    });
})();
