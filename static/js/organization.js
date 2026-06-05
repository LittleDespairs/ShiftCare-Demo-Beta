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
    const ALL_MEMBER_ROLES = ["owner", "admin", "scheduler", "manager", "read_only", "employee"];
    const ADMIN_ASSIGNABLE_ROLES = ["scheduler", "manager", "read_only", "employee"];
    const INVITE_ROLES = ["employee", "read_only", "manager", "scheduler", "admin", "owner"];

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

    function invitationEmailMessage(response, createdFallback, sentFallback) {
        const status = response?.email_status?.status || "";
        if (status === "sent" || status === "sent_by_cloud") {
            return uiText("org_msg_invitation_email_sent", sentFallback);
        }
        if (status === "failed") {
            return uiText("org_msg_invitation_email_failed", "Invitation created, but email delivery failed. Copy the link and send it manually.");
        }
        if (status === "disabled") {
            return uiText("org_msg_invitation_email_disabled", "Invitation created. Email delivery is not configured, so copy the link and send it manually.");
        }
        return uiText("org_msg_invitation_created", createdFallback);
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

    function isEmployeeRole(role) {
        return role === "employee";
    }

    function canManagePrivilegedRoles() {
        return state.membership?.role === "owner";
    }

    function assignableRolesForCurrentUser() {
        return canManagePrivilegedRoles() ? ALL_MEMBER_ROLES : ADMIN_ASSIGNABLE_ROLES;
    }

    function canManageMemberRole(member) {
        if (!canManageInvitations()) return false;
        if (!member || member.membership_status !== "active") return false;
        if (Number(member.user_id) === Number(state.user?.id)) return false;
        if (state.membership?.role !== "owner" && ["owner", "admin"].includes(member.role)) return false;
        return true;
    }

    function canManageMemberEmployeeLink(member) {
        return canManageInvitations()
            && member?.membership_status === "active"
            && member.role === "employee";
    }

    function roleOptions(currentRole, roles = assignableRolesForCurrentUser()) {
        const roleSet = new Set(roles);
        if (currentRole) roleSet.add(currentRole);
        return ALL_MEMBER_ROLES
            .filter((role) => roleSet.has(role))
            .map((role) => `<option value="${role}" ${role === currentRole ? "selected" : ""}>${text(formatRole(role))}</option>`)
            .join("");
    }

    function inviteRoleOptions() {
        const roles = canManagePrivilegedRoles() ? INVITE_ROLES : INVITE_ROLES.filter((role) => !["owner", "admin"].includes(role));
        return roles
            .map((role) => `<option value="${role}">${text(formatRole(role))}</option>`)
            .join("");
    }

    function inviteRoleHint(role) {
        if (role === "employee") {
            return uiText("org_role_hint_employee", "Employee access requires linking this account to an employee record.");
        }
        if (role === "read_only") {
            return uiText("org_role_hint_read_only", "Observer can view schedules and organization information without editing.");
        }
        if (role === "manager") {
            return uiText("org_role_hint_manager", "Manager can view schedule workflows and weekly preferences without schedule editing.");
        }
        if (role === "scheduler") {
            return uiText("org_role_hint_scheduler", "Scheduler can edit schedules and employee setup but cannot manage owners.");
        }
        if (role === "admin") {
            return uiText("org_role_hint_admin", "Admin can manage schedules, employees, invitations, and most organization settings.");
        }
        if (role === "owner") {
            return uiText("org_role_hint_owner", "Owner has full access and can manage other owners and admins.");
        }
        return "";
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
                <td>${renderMemberRoleCell(member)}</td>
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

    function renderMemberRoleCell(member) {
        if (!canManageMemberRole(member)) {
            return text(formatRole(member.role));
        }
        return `
            <select
                class="organization-table-select compact"
                data-organization-action="member-role"
                data-user-id="${Number(member.user_id)}"
                data-current-role="${text(member.role)}"
            >
                ${roleOptions(member.role)}
            </select>
        `;
    }

    function renderMemberEmployeeCell(member) {
        if (member.role !== "employee") return "";
        if (!canManageMemberEmployeeLink(member)) {
            return text(member.employee_name || uiText("org_member_employee_not_linked", "Not linked"));
        }
        return `
            <select
                class="organization-table-select"
                data-organization-action="member-employee-link"
                data-user-id="${Number(member.user_id)}"
                data-current-employee-id="${Number(member.employee_id || 0)}"
            >
                ${employeeLinkOptions(member.employee_id)}
            </select>
            ${member.employee_id ? "" : `<span class="organization-table-note">${text(uiText("org_member_employee_not_linked", "Not linked"))}</span>`}
        `;
    }

    function employeeLinkOptions(currentEmployeeId) {
        const linkedIds = linkedEmployeeIds(Number(currentEmployeeId || 0));
        const currentValue = Number(currentEmployeeId || 0);
        return [
            `<option value="">${text(uiText("org_no_employee_link", "No employee link"))}</option>`,
            ...state.employees.map((employee) => {
                const employeeId = Number(employee.id);
                const disabled = linkedIds.has(employeeId) && employeeId !== currentValue ? "disabled" : "";
                const selected = employeeId === currentValue ? "selected" : "";
                return `<option value="${employeeId}" ${disabled} ${selected}>${text(employee.full_name)}</option>`;
            }),
        ].join("");
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
            setMessage(invitationEmailMessage(response, "Invitation link generated.", "New invitation link emailed."), "success");
        } catch (error) {
            setMessage(error.message, "error");
        }
    }

    async function updateMemberRole(userId, role, selectElement) {
        setMessage(uiText("org_msg_updating_role", "Updating role..."), "");
        try {
            await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/members/${userId}/role`, {
                method: "PUT",
                body: JSON.stringify({ role }),
            });
            await refreshCurrentUser();
            renderOrganizationSelector();
            renderIdentity();
            renderPermissions();
            await loadOrganizationData();
            renderEmployeeSelector();
            setMessage(uiText("org_msg_role_updated", "Role updated."), "success");
        } catch (error) {
            if (selectElement?.dataset.currentRole) {
                selectElement.value = selectElement.dataset.currentRole;
            }
            setMessage(error.message, "error");
        }
    }

    async function updateMemberEmployeeLink(userId, employeeId, selectElement) {
        setMessage(uiText("org_msg_updating_employee_link", "Updating employee link..."), "");
        try {
            await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/members/${userId}/employee-link`, {
                method: "PUT",
                body: JSON.stringify({ employee_id: employeeId || null }),
            });
            await loadOrganizationData();
            renderEmployeeSelector();
            setMessage(uiText("org_msg_employee_link_updated", "Employee link updated."), "success");
        } catch (error) {
            if (selectElement?.dataset.currentEmployeeId) {
                selectElement.value = selectElement.dataset.currentEmployeeId === "0" ? "" : selectElement.dataset.currentEmployeeId;
            }
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

    function linkedEmployeeIds(allowedEmployeeId = 0) {
        const ids = new Set();
        (state.members || []).forEach((member) => {
            const employeeId = Number(member.employee_id || 0);
            if (employeeId && employeeId !== Number(allowedEmployeeId || 0) && member.membership_status === "active") {
                ids.add(employeeId);
            }
        });
        (state.invitations || []).forEach((invitation) => {
            const employeeId = Number(invitation.employee_id || 0);
            if (employeeId && employeeId !== Number(allowedEmployeeId || 0) && invitation.status === "pending") {
                ids.add(employeeId);
            }
        });
        return ids;
    }

    function linkedEmployeePublicIds(allowedEmployeePublicId = "") {
        const ids = new Set();
        const allowedValue = String(allowedEmployeePublicId || "").trim();
        (state.members || []).forEach((member) => {
            const employeePublicId = String(member.employee_public_id || "").trim();
            if (employeePublicId && employeePublicId !== allowedValue && member.membership_status === "active") {
                ids.add(employeePublicId);
            }
        });
        (state.invitations || []).forEach((invitation) => {
            const employeePublicId = String(invitation.employee_public_id || "").trim();
            if (employeePublicId && employeePublicId !== allowedValue && invitation.status === "pending") {
                ids.add(employeePublicId);
            }
        });
        return ids;
    }

    function renderEmployeeSelector() {
        if (!elements.inviteEmployee) return;
        const selectedRole = elements.inviteRole?.value || "employee";
        const employeeRequired = isEmployeeRole(selectedRole);
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
        elements.inviteEmployee.required = employeeRequired;
        elements.inviteEmployee.disabled = !employeeRequired;
        if (!employeeRequired) {
            elements.inviteEmployee.value = "";
        }
    }

    function updateInviteRoleState() {
        if (!elements.inviteRole) return;
        const currentRole = elements.inviteRole.value || "employee";
        elements.inviteRole.innerHTML = inviteRoleOptions();
        if ([...elements.inviteRole.options].some((option) => option.value === currentRole)) {
            elements.inviteRole.value = currentRole;
        }
        const role = elements.inviteRole.value || "employee";
        if (elements.inviteEmployeeField) {
            elements.inviteEmployeeField.hidden = !isEmployeeRole(role);
        }
        if (elements.inviteRoleHint) {
            elements.inviteRoleHint.textContent = inviteRoleHint(role);
        }
        renderEmployeeSelector();
    }

    function bindInviteForm() {
        elements.inviteForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!canManageInvitations()) return;
            setInviteResult("");
            setMessage(uiText("org_msg_creating_invitation", "Creating invitation..."), "");
            const selectedRole = elements.inviteRole.value || "employee";
            const isEmployeeInvitation = isEmployeeRole(selectedRole);
            if (isEmployeeInvitation && !elements.inviteEmployee.value) {
                setMessage(uiText("org_msg_select_employee_first", "Select an employee before creating an employee invitation."), "error");
                elements.inviteEmployee.focus();
                return;
            }
            try {
                const payload = {
                    email: elements.inviteEmail.value,
                    role: selectedRole,
                    expires_in_days: Number(elements.inviteDays.value),
                };
                if (isEmployeeInvitation) {
                    payload.employee_id = Number(elements.inviteEmployee.value);
                }
                const response = await window.scheduleAuth.request(`/api/organizations/${state.organizationId}/invitations`, {
                    method: "POST",
                    body: JSON.stringify(payload),
                });
                setInviteResult(invitationUrlFromResponse(response));
                elements.inviteForm.reset();
                elements.inviteDays.value = "7";
                updateInviteRoleState();
                await loadOrganizationData();
                renderEmployeeSelector();
                setMessage(invitationEmailMessage(response, "Invitation created.", "Invitation emailed."), "success");
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
            updateInviteRoleState();
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
        elements.inviteRole?.addEventListener("change", updateInviteRoleState);
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
        elements.membersBody.addEventListener("change", (event) => {
            const roleSelect = event.target.closest('[data-organization-action="member-role"]');
            if (roleSelect) {
                updateMemberRole(Number(roleSelect.dataset.userId), roleSelect.value, roleSelect);
                return;
            }
            const employeeSelect = event.target.closest('[data-organization-action="member-employee-link"]');
            if (employeeSelect) {
                updateMemberEmployeeLink(Number(employeeSelect.dataset.userId), Number(employeeSelect.value || 0), employeeSelect);
            }
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
            inviteEmployeeField: document.getElementById("invite-employee-field"),
            inviteEmployee: document.getElementById("invite-employee"),
            inviteEmail: document.getElementById("invite-email"),
            inviteRole: document.getElementById("invite-role"),
            inviteRoleHint: document.getElementById("invite-role-hint"),
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
            updateInviteRoleState();
            await loadOrganizationData();
            await loadEmployeesForInvitations();
            await loadCloudLinkStatus();
        } catch (error) {
            setMessage(error.message, "error");
        }
    });
})();
