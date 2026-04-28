(function () {
    const state = {
        user: null,
        organizationId: null,
        organizationName: "",
        membership: null,
    };

    const elements = {};
    const INVITATION_ROLES = new Set(["owner", "admin"]);
    const MEMBER_VIEW_ROLES = new Set(["owner", "admin", "scheduler", "manager"]);

    function text(value) {
        return window.escapeHtml ? window.escapeHtml(value) : String(value ?? "");
    }

    function setMessage(value, type = "") {
        elements.message.textContent = value || "";
        elements.message.className = `organization-message ${type}`.trim();
    }

    function setInviteResult(value) {
        elements.inviteResult.value = value || "";
        elements.inviteResultWrap.hidden = !value;
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
            elements.membersBody.innerHTML = `<tr><td colspan="5">${text(emptyMessage)}</td></tr>`;
            return;
        }
        elements.membersBody.innerHTML = members.map((member) => `
            <tr>
                <td>${text(member.full_name)}</td>
                <td>${text(member.email)}</td>
                <td>${text(member.role)}</td>
                <td>${text(member.membership_status)}</td>
                <td>${member.email_verified ? "Yes" : "No"}</td>
            </tr>
        `).join("");
    }

    function renderInvitations(invitations, emptyMessage = "No invitations found.") {
        if (!invitations.length) {
            elements.invitationsBody.innerHTML = `<tr><td colspan="5">${text(emptyMessage)}</td></tr>`;
            return;
        }
        elements.invitationsBody.innerHTML = invitations.map((invitation) => `
            <tr>
                <td>${text(invitation.email)}</td>
                <td>${text(invitation.role)}</td>
                <td>${text(invitation.status)}</td>
                <td>${text(invitation.expires_at)}</td>
                <td>${text(invitation.accepted_at || "")}</td>
            </tr>
        `).join("");
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
                        role: elements.inviteRole.value,
                        expires_in_days: Number(elements.inviteDays.value),
                    }),
                });
                const token = response.invitation_token;
                const acceptUrl = `${window.location.origin}/accept-invitation?token=${encodeURIComponent(token)}`;
                setInviteResult(acceptUrl);
                elements.inviteForm.reset();
                elements.inviteDays.value = "7";
                await loadOrganizationData();
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

    function bindActions() {
        elements.organizationSelect.addEventListener("change", async () => {
            window.scheduleAuth.setActiveOrganizationId(Number(elements.organizationSelect.value));
            selectMembership();
            renderIdentity();
            renderPermissions();
            setMessage("", "");
            try {
                await loadOrganizationData();
            } catch (error) {
                setMessage(error.message, "error");
            }
        });
        elements.copyInvite.addEventListener("click", async () => {
            if (!elements.inviteResult.value) return;
            await navigator.clipboard.writeText(elements.inviteResult.value);
            setMessage("Invitation link copied.", "success");
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
            inviteEmail: document.getElementById("invite-email"),
            inviteRole: document.getElementById("invite-role"),
            inviteDays: document.getElementById("invite-days"),
            inviteResult: document.getElementById("invite-result"),
            inviteResultWrap: document.getElementById("invite-result-wrap"),
            copyInvite: document.getElementById("copy-invite-btn"),
            logout: document.getElementById("logout-btn"),
        });

        state.user = window.scheduleAuth.requireSession();
        if (!state.user) return;
        bindInviteForm();
        bindProfileForms();
        bindActions();
        try {
            await refreshCurrentUser();
            renderOrganizationSelector();
            renderIdentity();
            renderPermissions();
            await loadOrganizationData();
        } catch (error) {
            setMessage(error.message, "error");
        }
    });
})();
