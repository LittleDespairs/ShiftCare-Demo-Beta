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
        if (typeof window.translate === "function") {
            const translated = window.translate(key);
            return translated === key ? (fallback || key) : translated;
        }
        return fallback || key;
    }

    function setupSidebarToggle() {
        const toggle = document.getElementById("sidebar-toggle");
        if (!toggle) return;
        const applyResponsiveState = () => {
            document.body.classList.remove("sidebar-collapsed", "mobile-sidebar-hidden");
            if (window.matchMedia("(max-width: 920px)").matches) {
                document.body.classList.add("mobile-sidebar-hidden");
                return;
            }
            if (localStorage.getItem("sidebarCollapsed") === "true") {
                document.body.classList.add("sidebar-collapsed");
            }
        };
        toggle.addEventListener("click", () => {
            if (window.matchMedia("(max-width: 920px)").matches) {
                document.body.classList.toggle("mobile-sidebar-hidden");
                return;
            }
            const collapsedNow = !document.body.classList.contains("sidebar-collapsed");
            document.body.classList.toggle("sidebar-collapsed", collapsedNow);
            localStorage.setItem("sidebarCollapsed", collapsedNow ? "true" : "false");
        });
        window.addEventListener("resize", applyResponsiveState);
        applyResponsiveState();
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
        if (elements.openInviteLink) {
            elements.openInviteLink.href = value || "#";
            elements.openInviteLink.setAttribute("aria-disabled", value ? "false" : "true");
        }
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
        const publicBaseUrl = configuredPublicBaseUrl();
        const cloudBaseUrl = window.scheduleAuth?.CLOUD_API_FALLBACK_BASE_URL || window.scheduleAuth?.CLOUD_API_BASE_URL || "";
        const rawUrl = String(response.invitation_url || "").trim();
        if (/^https?:\/\//i.test(rawUrl)) return rawUrl;
        if (rawUrl.startsWith("/") && publicBaseUrl) return `${publicBaseUrl}${rawUrl}`;
        if (rawUrl.startsWith("/") && cloudBaseUrl) return `${cloudBaseUrl.replace(/\/+$/, "")}${rawUrl}`;
        const token = response.invitation_token || "";
        if (publicBaseUrl && token) {
            return `${publicBaseUrl}/accept-invitation?token=${encodeURIComponent(token)}`;
        }
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
            <span>${text(state.membership?.organization_name || uiText("org_no_organization", "No organization"))} · ${text(formatRole(state.membership?.role || "no role"))}</span>
        `;
        elements.title.textContent = state.organizationName || uiText("org_title", "Organization");
        elements.profileName.value = state.user.full_name || "";
        elements.profileEmail.value = state.user.email || "";
    }

    function renderEmployeePortal() {
        if (!elements.employeePortalUrl) return;
        const url = employeePortalUrl();
        elements.employeePortalUrl.value = url || uiText("org_employee_portal_not_configured", "Employee portal URL is not configured.");
        if (elements.copyEmployeePortal) {
            elements.copyEmployeePortal.disabled = !url;
        }
        if (elements.openEmployeePortalLink) {
            elements.openEmployeePortalLink.href = url || "#";
            elements.openEmployeePortalLink.setAttribute("aria-disabled", url ? "false" : "true");
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

    function formatRole(role) {
        return uiText(`org_role_${role}`, role || "-");
    }

    function formatStatus(status) {
        return uiText(`org_status_${status}`, status || "-");
    }

    function yesNo(value) {
        return value ? uiText("common_yes", "Yes") : uiText("common_no", "No");
    }

    function renderMembers(members, emptyMessage = uiText("org_no_members", "No members found.")) {
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
                <td>${text(formatRole(member.role))}</td>
                <td>${text(formatStatus(member.membership_status))}</td>
                <td>${text(yesNo(member.email_verified))}</td>
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

    function renderInvitations(invitations, emptyMessage = uiText("org_no_invitations", "No invitations found.")) {
        state.invitations = invitations;
        if (!invitations.length) {
            elements.invitationsBody.innerHTML = `<tr><td colspan="7">${text(emptyMessage)}</td></tr>`;
            return;
        }
        elements.invitationsBody.innerHTML = invitations.map((invitation) => `
            <tr>
                <td>${text(invitation.email)}</td>
                <td>${text(invitation.employee_name || "")}</td>
                <td>${text(formatRole(invitation.role))}</td>
                <td>${text(formatStatus(invitation.status))}</td>
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
            setMessage(uiText("org_msg_no_active_organization", "Current user has no active organization."), "error");
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
            setMessage(uiText("org_msg_creating_invitation", "Creating invitation..."), "");
            if (!elements.inviteEmployee.value) {
                setMessage(uiText("org_msg_select_employee_first", "Select an employee before creating an employee invitation."), "error");
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
                setMessage(uiText("org_msg_invitation_created", "Invitation created."), "success");
            } catch (error) {
                setMessage(error.message, "error");
            }
        });
    }

    function bindProfileForms() {
        elements.profileForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            setMessage(uiText("org_msg_saving_profile", "Saving profile..."), "");
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
                setMessage(uiText("org_msg_profile_saved", "Profile saved."), "success");
            } catch (error) {
                setMessage(error.message, "error");
            }
        });

        elements.passwordForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            setMessage(uiText("org_msg_changing_password", "Changing password..."), "");
            try {
                await window.scheduleAuth.request("/api/auth/change-password", {
                    method: "POST",
                    body: JSON.stringify({
                        current_password: elements.currentPassword.value,
                        new_password: elements.newPassword.value,
                    }),
                });
                elements.passwordForm.reset();
                setMessage(uiText("org_msg_password_changed", "Password changed."), "success");
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
                setCloudStatus(uiText("org_cloud_not_connected", "Cloud portal is optional and is not connected for this local organization."), "");
            }
        } catch (error) {
            renderCloudLinkSummary(null);
        }
    }

    function isRetryableCloudStatus(status) {
        return [429, 502, 503, 504].includes(Number(status));
    }

    function cloudRetryDelay(attempt, response) {
        const retryAfter = Number(response?.headers?.get("Retry-After"));
        if (Number.isFinite(retryAfter) && retryAfter >= 0) {
            return Math.min(30000, retryAfter * 1000);
        }
        return Math.min(8000, 1000 * (2 ** attempt));
    }

    async function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function cloudRequest(baseUrl, path, options = {}, token = "") {
        const headers = new Headers(options.headers || {});
        if (token) headers.set("Authorization", `Bearer ${token}`);
        if (options.body && !headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }

        let lastError = null;
        for (let attempt = 0; attempt < 3; attempt += 1) {
            const controller = new AbortController();
            const timeoutId = window.setTimeout(() => controller.abort(), 45000);
            try {
                const response = await window.scheduleAuth.nativeFetch(`${baseUrl}${path}`, {
                    ...options,
                    headers,
                    signal: controller.signal
                });
                const data = await response.json().catch(() => ({}));
                if (response.ok) {
                    return data;
                }
                if (isRetryableCloudStatus(response.status) && attempt < 2) {
                    await sleep(cloudRetryDelay(attempt, response));
                    continue;
                }
                const error = new Error(data.detail || `Cloud request failed with ${response.status}`);
                error.nonRetryable = true;
                throw error;
            } catch (error) {
                lastError = error;
                if (error?.nonRetryable || attempt >= 2) break;
                await sleep(cloudRetryDelay(attempt));
            } finally {
                window.clearTimeout(timeoutId);
            }
        }
        throw lastError || new Error("Cloud request failed");
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
            setCloudStatus(uiText("org_cloud_only_admin_connect", "Only owners and admins can connect this organization to cloud."), "error");
            return;
        }
        const cloudBaseUrl = normalizeCloudApiBaseUrl(elements.cloudApiBaseUrl.value);
        if (!cloudBaseUrl) {
            setCloudStatus(uiText("org_cloud_enter_valid_url", "Enter a valid Cloud API URL."), "error");
            return;
        }
        setMessage("", "");
        setCloudStatus(uiText("org_cloud_preparing_export", "Preparing local organization export..."), "");
        try {
            const localBundle = await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/cloud-export`);
            setCloudStatus(uiText("org_cloud_signing_in", "Signing in to Cloud beta API..."), "");
            const cloudSession = await loginOrBootstrapCloud(cloudBaseUrl);
            const cloudMembership = getCloudMembership(cloudSession.user);
            if (!cloudMembership || !["owner", "admin"].includes(cloudMembership.role)) {
                throw new Error(uiText("org_cloud_owner_required", "Cloud account must be an owner or admin of the target organization."));
            }
            setCloudStatus(uiText("org_cloud_uploading", "Uploading local organization to cloud..."), "");
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
            setCloudStatus(uiText("org_cloud_saving_link", "Saving cloud link locally..."), "");
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
                uiText("org_cloud_linked_imported", "Linked. Imported {employees} employees, {positions} positions, {shift_templates} shift templates.")
                    .replace("{employees}", importResponse.imported.employees)
                    .replace("{positions}", importResponse.imported.positions)
                    .replace("{shift_templates}", importResponse.imported.shift_templates),
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
            setCloudStatus(uiText("org_cloud_only_admin_disconnect", "Only owners and admins can disconnect the cloud portal."), "error");
            return;
        }
        setCloudStatus(uiText("org_cloud_disconnecting", "Disconnecting cloud portal..."), "");
        try {
            await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/cloud-link`, {
                method: "DELETE",
            });
            renderCloudLinkSummary(null);
            setCloudStatus(uiText("org_cloud_disconnected", "Cloud portal disconnected for this local organization."), "success");
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
            setMessage(uiText("org_msg_invitation_copied", "Invitation link copied."), "success");
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
        setupSidebarToggle();
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
            openInviteLink: document.getElementById("open-invite-link"),
            copyInvite: document.getElementById("copy-invite-btn"),
            employeePortalUrl: document.getElementById("employee-portal-url"),
            openEmployeePortalLink: document.getElementById("open-employee-portal-link"),
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
