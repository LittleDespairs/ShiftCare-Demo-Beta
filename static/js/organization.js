(function () {
    const state = {
        user: null,
        organizationId: null,
        organizationName: "",
    };

    const elements = {};

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

    function getPrimaryMembership(user) {
        return user?.memberships?.find((membership) => membership.status === "active") || user?.memberships?.[0] || null;
    }

    async function refreshCurrentUser() {
        const response = await window.scheduleAuth.request("/api/auth/me");
        window.scheduleAuth.setSession({
            access_token: window.scheduleAuth.getToken(),
            user: response.user,
        });
        state.user = response.user;
        const membership = getPrimaryMembership(response.user);
        state.organizationId = membership?.organization_id || null;
        state.organizationName = membership?.organization_name || "";
    }

    function renderIdentity() {
        const membership = getPrimaryMembership(state.user);
        elements.identity.innerHTML = `
            <strong>${text(state.user.full_name)}</strong>
            <span>${text(state.user.email)}</span>
            <span>${text(membership?.organization_name || "No organization")} · ${text(membership?.role || "no role")}</span>
        `;
        elements.title.textContent = state.organizationName || "Organization";
    }

    function renderMembers(members) {
        if (!members.length) {
            elements.membersBody.innerHTML = `<tr><td colspan="5">No members found.</td></tr>`;
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

    function renderInvitations(invitations) {
        if (!invitations.length) {
            elements.invitationsBody.innerHTML = `<tr><td colspan="5">No invitations found.</td></tr>`;
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
        const [membersResponse, invitationsResponse] = await Promise.all([
            window.scheduleAuth.request(`/api/organizations/${state.organizationId}/members`),
            window.scheduleAuth.request(`/api/organizations/${state.organizationId}/invitations`),
        ]);
        renderMembers(membersResponse.members || []);
        renderInvitations(invitationsResponse.invitations || []);
    }

    function bindInviteForm() {
        elements.inviteForm.addEventListener("submit", async (event) => {
            event.preventDefault();
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

    function bindActions() {
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
        bindActions();
        try {
            await refreshCurrentUser();
            renderIdentity();
            await loadOrganizationData();
        } catch (error) {
            setMessage(error.message, "error");
        }
    });
})();
