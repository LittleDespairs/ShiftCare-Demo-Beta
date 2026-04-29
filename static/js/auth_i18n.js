(function () {
    const translations = {
        en: {
            app_title: "ShiftCare",
            auth_kicker: "ShiftCare 0.14.x beta",
            auth_login: "Login",
            auth_create_owner: "Create first owner",
            auth_email: "Email",
            auth_password: "Password",
            auth_org_access: "Organization access",
            auth_org_name: "Organization name",
            auth_your_name: "Your name",
            auth_create_owner_account: "Create owner account",
            auth_foundation: "User authorization foundation",
            auth_foundation_text: "Cloud is the primary workspace. Local mode is kept for migration, backups, and emergency access.",
            auth_connection: "Connection",
            auth_local_recovery: "Local recovery and migration",
            auth_accept_title: "Accept invitation",
            auth_create_account: "Create your account",
            auth_invitation_token: "Invitation token",
            auth_accept_button: "Accept invitation",
            auth_employee_access: "Employee access",
            auth_join_org: "Join your organization",
            auth_join_text: "Use the invitation link from your administrator to create your own account.",
            org_title: "Organization",
            org_subtitle: "Members, roles, and employee invitation links.",
            org_account: "Account",
            org_account_text: "Profile details and password.",
            org_full_name: "Full name",
            org_save_profile: "Save profile",
            org_current_password: "Current password",
            org_new_password: "New password",
            org_change_password: "Change password",
            org_invite: "Invite employee",
            org_invite_text: "Create a one-time invitation link.",
            org_role: "Role",
            org_expires: "Expires in days",
            org_create_invitation: "Create invitation",
            org_employee_portal: "Employee portal",
            org_employee_portal_text: "Public login page for employees.",
            org_employee_site_address: "Employee site address",
            org_cloud_link: "Cloud connection",
            org_cloud_link_text: "Upload this local organization to the Cloud beta API and link this installation to it.",
            org_cloud_api: "Cloud API",
            org_cloud_email: "Cloud owner email",
            org_cloud_password: "Cloud owner password",
            org_cloud_replace: "Replace scheduling data in the selected cloud organization",
            org_cloud_upload: "Upload and link cloud organization",
            org_cloud_linked_status: "This installation is linked to cloud.",
            org_cloud_linked_api: "Linked Cloud API",
            org_cloud_linked_org: "Cloud organization",
            org_cloud_linked_at: "Linked at",
            org_members: "Members",
            org_members_text: "Active users and organization roles.",
            org_invitations: "Invitations",
            org_invitations_text: "Pending, accepted, expired, and revoked links.",
            common_logout: "Logout",
            nav_home: "Home",
            nav_schedule: "Schedule",
            nav_settings: "Settings",
            org_selector: "Organization",
            org_invitation_link: "Invitation link",
            org_employee: "Employee",
            org_no_employee_link: "No employee link",
            org_copy_link: "Copy link",
            org_table_name: "Name",
            org_table_status: "Status",
            org_email_verified: "Email verified",
            org_table_accepted: "Accepted",
            org_table_actions: "Actions",
            org_remove_member: "Remove",
            org_revoke_invitation: "Revoke",
            org_regenerate_invitation: "New link",
            org_msg_confirm_remove_member: "Remove this member from the organization?",
            org_msg_confirm_revoke_invitation: "Revoke this invitation link?",
            org_msg_member_removed: "Member access removed.",
            org_msg_invitation_revoked: "Invitation revoked.",
            org_msg_invitation_link_generated: "Invitation link generated.",
            org_msg_employee_portal_copied: "Employee portal link copied.",
            common_delete: "Delete",
        },
        ru: {
            app_title: "ShiftCare",
            auth_kicker: "ShiftCare 0.14.x beta",
            auth_login: "Войти",
            auth_create_owner: "Создать владельца",
            auth_email: "Email",
            auth_password: "Пароль",
            auth_org_access: "Доступ к организации",
            auth_org_name: "Название организации",
            auth_your_name: "Ваше имя",
            auth_create_owner_account: "Создать аккаунт владельца",
            auth_foundation: "Основа пользовательской авторизации",
            auth_foundation_text: "Основное рабочее пространство находится в облаке. Локальный режим оставлен для переноса, резервных копий и аварийного доступа.",
            auth_connection: "Подключение",
            auth_local_recovery: "Локальное восстановление и перенос",
            auth_accept_title: "Принять приглашение",
            auth_create_account: "Создайте аккаунт",
            auth_invitation_token: "Токен приглашения",
            auth_accept_button: "Принять приглашение",
            auth_employee_access: "Доступ сотрудника",
            auth_join_org: "Присоединиться к организации",
            auth_join_text: "Используйте ссылку приглашения от администратора, чтобы создать свой аккаунт.",
            org_title: "Организация",
            org_subtitle: "Участники, роли и ссылки приглашений сотрудников.",
            org_account: "Аккаунт",
            org_account_text: "Профиль и пароль.",
            org_full_name: "Полное имя",
            org_save_profile: "Сохранить профиль",
            org_current_password: "Текущий пароль",
            org_new_password: "Новый пароль",
            org_change_password: "Сменить пароль",
            org_invite: "Пригласить сотрудника",
            org_invite_text: "Создайте одноразовую ссылку приглашения.",
            org_role: "Роль",
            org_expires: "Действует дней",
            org_create_invitation: "Создать приглашение",
            org_employee_portal: "Портал сотрудников",
            org_employee_portal_text: "Публичная страница входа для сотрудников.",
            org_employee_site_address: "Адрес сайта для сотрудников",
            org_cloud_link: "Подключение к облаку",
            org_cloud_link_text: "Загрузите эту локальную организацию в Cloud beta API и привяжите эту установку к ней.",
            org_cloud_api: "Cloud API",
            org_cloud_email: "Email владельца в облаке",
            org_cloud_password: "Пароль владельца в облаке",
            org_cloud_replace: "Заменить данные расписания в выбранной облачной организации",
            org_cloud_upload: "Загрузить и привязать облачную организацию",
            org_cloud_linked_status: "Эта установка привязана к облаку.",
            org_cloud_linked_api: "Привязанный Cloud API",
            org_cloud_linked_org: "Облачная организация",
            org_cloud_linked_at: "Дата привязки",
            org_members: "Участники",
            org_members_text: "Активные пользователи и роли организации.",
            org_invitations: "Приглашения",
            org_invitations_text: "Ожидающие, принятые, истёкшие и отозванные ссылки.",
            common_logout: "Выйти",
            nav_home: "Главная",
            nav_schedule: "Расписание",
            nav_settings: "Настройки",
            org_selector: "Организация",
            org_invitation_link: "Ссылка приглашения",
            org_employee: "Сотрудник",
            org_no_employee_link: "Без привязки к сотруднику",
            org_copy_link: "Копировать ссылку",
            org_table_name: "Имя",
            org_table_status: "Статус",
            org_email_verified: "Email подтверждён",
            org_table_accepted: "Принято",
            org_table_actions: "Действия",
            org_remove_member: "Удалить",
            org_revoke_invitation: "Отозвать",
            org_regenerate_invitation: "Новая ссылка",
            org_msg_confirm_remove_member: "Удалить этого участника из организации?",
            org_msg_confirm_revoke_invitation: "Отозвать эту ссылку приглашения?",
            org_msg_member_removed: "Доступ участника удалён.",
            org_msg_invitation_revoked: "Приглашение отозвано.",
            org_msg_invitation_link_generated: "Ссылка приглашения создана.",
            org_msg_employee_portal_copied: "Ссылка портала сотрудников скопирована.",
            common_delete: "Удалить",
        },
        he: {
            app_title: "ShiftCare",
            auth_kicker: "ShiftCare 0.14.x beta",
            auth_login: "כניסה",
            auth_create_owner: "יצירת בעלים ראשון",
            auth_email: "אימייל",
            auth_password: "סיסמה",
            auth_org_access: "גישה לארגון",
            auth_org_name: "שם הארגון",
            auth_your_name: "השם שלך",
            auth_create_owner_account: "צור חשבון בעלים",
            auth_foundation: "בסיס הרשאות משתמשים",
            auth_foundation_text: "הענן הוא סביבת העבודה הראשית. מצב מקומי נשמר להעברה, גיבויים וגישה בחירום.",
            auth_connection: "חיבור",
            auth_local_recovery: "שחזור והעברה מקומית",
            auth_accept_title: "קבלת הזמנה",
            auth_create_account: "יצירת חשבון",
            auth_invitation_token: "טוקן הזמנה",
            auth_accept_button: "קבל הזמנה",
            auth_employee_access: "גישת עובד",
            auth_join_org: "הצטרפות לארגון",
            auth_join_text: "השתמש בקישור ההזמנה מהאדמין כדי ליצור חשבון.",
            org_title: "ארגון",
            org_subtitle: "חברים, תפקידים וקישורי הזמנה לעובדים.",
            org_account: "חשבון",
            org_account_text: "פרטי פרופיל וסיסמה.",
            org_full_name: "שם מלא",
            org_save_profile: "שמור פרופיל",
            org_current_password: "סיסמה נוכחית",
            org_new_password: "סיסמה חדשה",
            org_change_password: "שנה סיסמה",
            org_invite: "הזמן עובד",
            org_invite_text: "צור קישור הזמנה חד-פעמי.",
            org_role: "תפקיד",
            org_expires: "תוקף בימים",
            org_create_invitation: "צור הזמנה",
            org_employee_portal: "פורטל עובדים",
            org_employee_portal_text: "עמוד כניסה ציבורי לעובדים.",
            org_employee_site_address: "כתובת אתר לעובדים",
            org_cloud_link: "חיבור לענן",
            org_cloud_link_text: "העלה את הארגון המקומי ל-Cloud beta API וקשר את ההתקנה הזו אליו.",
            org_cloud_api: "Cloud API",
            org_cloud_email: "אימייל בעלים בענן",
            org_cloud_password: "סיסמת בעלים בענן",
            org_cloud_replace: "החלף נתוני סידור בארגון הענן שנבחר",
            org_cloud_upload: "העלה וקשר ארגון ענן",
            org_cloud_linked_status: "התקנה זו מקושרת לענן.",
            org_cloud_linked_api: "Cloud API מקושר",
            org_cloud_linked_org: "ארגון ענן",
            org_cloud_linked_at: "זמן קישור",
            org_members: "חברים",
            org_members_text: "משתמשים פעילים ותפקידי הארגון.",
            org_invitations: "הזמנות",
            org_invitations_text: "קישורים ממתינים, התקבלו, פגי תוקף ובוטלו.",
            common_logout: "יציאה",
            nav_home: "בית",
            nav_schedule: "סידור עבודה",
            nav_settings: "הגדרות",
            org_selector: "ארגון",
            org_invitation_link: "קישור הזמנה",
            org_employee: "עובד",
            org_no_employee_link: "ללא קישור לעובד",
            org_copy_link: "העתק קישור",
            org_table_name: "שם",
            org_table_status: "סטטוס",
            org_email_verified: "אימייל אומת",
            org_table_accepted: "התקבל",
            org_table_actions: "פעולות",
            org_remove_member: "הסר",
            org_revoke_invitation: "בטל",
            org_regenerate_invitation: "קישור חדש",
            org_msg_confirm_remove_member: "להסיר את החבר מהארגון?",
            org_msg_confirm_revoke_invitation: "לבטל את קישור ההזמנה?",
            org_msg_member_removed: "גישת החבר הוסרה.",
            org_msg_invitation_revoked: "ההזמנה בוטלה.",
            org_msg_invitation_link_generated: "קישור ההזמנה נוצר.",
            org_msg_employee_portal_copied: "קישור פורטל העובדים הועתק.",
            common_delete: "מחיקה",
        },
    };

    function language() {
        return localStorage.getItem("scheduleAppLanguage") || document.documentElement.lang || "en";
    }

    function t(key) {
        const lang = language();
        return (translations[lang] || translations.en)[key] || translations.en[key] || key;
    }

    function setText(selector, key) {
        document.querySelectorAll(selector).forEach((element) => {
            element.textContent = t(key);
        });
    }

    function applyAuthTranslations() {
        setText("#auth-title", "app_title");
        setText(".auth-brand p", document.getElementById("accept-title") ? "auth_create_account" : "auth_org_access");
        setText("#login-tab", "auth_login");
        setText("#bootstrap-tab", "auth_create_owner");
        setText('label[for="login-email"], #login-form label:nth-of-type(1) span, #bootstrap-form label:nth-of-type(3) span', "auth_email");
        setText('#login-form label:nth-of-type(2) span, #bootstrap-form label:nth-of-type(4) span, #accept-form label:nth-of-type(3) span', "auth_password");
        setText("#login-form .auth-submit", "auth_login");
        setText("#bootstrap-form label:nth-of-type(1) span", "auth_org_name");
        setText("#bootstrap-form label:nth-of-type(2) span, #accept-form label:nth-of-type(2) span", "auth_your_name");
        setText("#bootstrap-form .auth-submit", "auth_create_owner_account");
        setText(".auth-side h2", document.getElementById("accept-title") ? "auth_join_org" : "auth_foundation");
        setText(".auth-side-content > p:not(.auth-kicker):not(.api-mode-status):not(.api-mode-title)", document.getElementById("accept-title") ? "auth_join_text" : "auth_foundation_text");
        setText(".api-mode-title", "auth_connection");
        setText("#api-advanced-toggle", "auth_local_recovery");
        setText("#accept-title", "auth_accept_title");
        setText("#accept-form label:nth-of-type(1) span", "auth_invitation_token");
        setText("#accept-form .auth-submit", "auth_accept_button");
        setText(".auth-kicker", document.getElementById("accept-title") ? "auth_employee_access" : "auth_kicker");
        setText("#organization-title", "org_title");
        setText(".page-subtitle", "org_subtitle");
        setText("#logout-btn", "common_logout");
        setText(".nav-item[href='/'] .nav-label", "nav_home");
        setText(".nav-item[href='/schedule'] .nav-label", "nav_schedule");
        setText(".nav-item[href='/organization'] .nav-label", "org_title");
        setText(".nav-item[href='/settings'] .nav-label", "nav_settings");
        setText("#organization-selector-wrap span", "org_selector");
        setText("#profile-form label:nth-of-type(1) span", "org_full_name");
        setText("#profile-form label:nth-of-type(2) span", "auth_email");
        setText("#profile-form .btn", "org_save_profile");
        setText("#password-form label:nth-of-type(1) span", "org_current_password");
        setText("#password-form label:nth-of-type(2) span", "org_new_password");
        setText("#password-form .btn", "org_change_password");
        setText("#invite-form .settings-section-title", "org_invite");
        setText("#invite-form .settings-section-text", "org_invite_text");
        setText("#invite-form label:nth-of-type(1) span", "org_employee");
        setText("#invite-form label:nth-of-type(2) span", "auth_email");
        setText("#invite-form label:nth-of-type(3) span", "org_role");
        setText("#invite-form label:nth-of-type(4) span", "org_expires");
        setText("#invite-form > .btn", "org_create_invitation");
        setText("#employee-portal-panel .settings-section-title", "org_employee_portal");
        setText("#employee-portal-panel .settings-section-text", "org_employee_portal_text");
        setText("#employee-portal-panel label span", "org_employee_site_address");
        setText("#copy-employee-portal-btn", "org_copy_link");
        setText("#cloud-link-panel .settings-section-title", "org_cloud_link");
        setText("#cloud-link-panel .settings-section-text", "org_cloud_link_text");
        setText('label[for="cloud-api-base-url"] span, #cloud-link-form label:nth-of-type(1) span', "org_cloud_api");
        setText("#cloud-link-form label:nth-of-type(2) span", "org_cloud_email");
        setText("#cloud-link-form label:nth-of-type(3) span", "org_cloud_password");
        setText("#cloud-link-form .checkbox-row span", "org_cloud_replace");
        setText("#cloud-link-form > .btn", "org_cloud_upload");
        setText("#cloud-link-summary dt:nth-of-type(1)", "org_cloud_linked_api");
        setText("#cloud-link-summary div:nth-child(1) dt", "org_cloud_linked_api");
        setText("#cloud-link-summary div:nth-child(2) dt", "org_cloud_linked_org");
        setText("#cloud-link-summary div:nth-child(3) dt", "org_cloud_linked_at");
        setText("#invite-result-wrap label span", "org_invitation_link");
        setText("#copy-invite-btn", "org_copy_link");
        setText(".organization-table th:nth-child(1)", "org_table_name");
        setText(".organization-table th:nth-child(4)", "org_table_status");
        setText(".organization-table:first-of-type th:nth-child(5)", "org_email_verified");
        setText(".organization-table:first-of-type th:nth-child(6)", "org_table_actions");
        setText(".organization-panel-wide .organization-table th:nth-child(2)", "org_employee");
        setText(".organization-panel-wide .organization-table th:nth-child(5)", "org_expires");
        setText(".organization-panel-wide .organization-table th:nth-child(6)", "org_table_accepted");
        setText(".organization-panel-wide .organization-table th:nth-child(7)", "org_table_actions");

        const membersTable = document.getElementById("members-table-body")?.closest("table");
        const invitationsTable = document.getElementById("invitations-table-body")?.closest("table");
        [
            [membersTable, ["org_table_name", "auth_email", "org_employee", "org_role", "org_table_status", "org_email_verified", "org_table_actions"]],
            [invitationsTable, ["auth_email", "org_employee", "org_role", "org_table_status", "org_expires", "org_table_accepted", "org_table_actions"]],
        ].forEach(([table, keys]) => {
            if (!table) return;
            table.querySelectorAll("th").forEach((header, index) => {
                if (keys[index]) header.textContent = t(keys[index]);
            });
        });
    }

    window.organizationAuthText = t;

    document.addEventListener("DOMContentLoaded", applyAuthTranslations);
    document.addEventListener("app-language-changed", applyAuthTranslations);
})();
