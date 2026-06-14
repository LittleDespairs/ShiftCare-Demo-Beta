(function () {
    const translations = {
        en: {
            app_title: "ShiftCare",
            auth_kicker: "Desktop first",
            auth_login: "Login",
            auth_authorize_user: "Authorize user",
            auth_employee_login: "Employee login",
            auth_add_organization: "Add organization",
            auth_login_action_text: "Load organization data to this computer",
            auth_employee_login_action_text: "Open weekly wishes and read-only schedule",
            auth_add_organization_text: "Create a cloud organization and start locally",
            auth_employee_portal: "Employee portal",
            auth_login_method: "Login method",
            auth_id_card: "ID card",
            auth_id_card_placeholder: "Example: 123456789",
            auth_email_placeholder: "name@example.com",
            auth_create_organization: "Create organization",
            auth_initial_role: "Your role",
            auth_initial_role_hint: "The first account is always the organization owner.",
            auth_msg_cloud_unreachable: "Cloud is not reachable. Check the internet connection and try again.",
            auth_msg_desktop_ready: "Authorize a cloud user or add a new organization. Work will continue locally on this computer.",
            auth_msg_employee_portal_ready: "Employee portal is ready.",
            auth_msg_employee_login_ready: "Employee portal is ready. Log in with your employee account.",
            auth_msg_status_check_failed: "Could not check authorization state",
            auth_msg_signing_in: "Signing in...",
            auth_msg_signing_in_desktop: "Signing in and loading organization data...",
            auth_msg_login_success: "Login successful.",
            auth_msg_org_setup_desktop_only: "Organization setup is available only in the desktop app.",
            auth_msg_creating_org: "Creating organization...",
            auth_msg_creating_org_desktop: "Creating cloud organization and loading it locally...",
            auth_msg_org_created: "Organization created.",
            auth_create_owner: "Create first owner",
            auth_email: "Email",
            auth_password: "Password",
            auth_org_access: "Organization access",
            auth_org_name: "Organization name",
            auth_your_name: "Your name",
            auth_create_owner_account: "Create owner account",
            auth_foundation: "Local scheduling workspace",
            auth_foundation_text: "Sign in with your cloud account, load the organization data to this computer, and continue scheduling locally without waiting on the network.",
            auth_connection: "Connection",
            auth_local_recovery: "Cloud sync",
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
            org_invite: "Invite member",
            org_invite_text: "Email a one-time invitation link and choose the access role.",
            org_role: "Role",
            org_expires: "Expires in days",
            org_create_invitation: "Create invitation",
            org_employee_portal: "Employee portal",
            org_employee_portal_text: "Public employee login page for weekly wishes and read-only schedules.",
            org_employee_site_address: "Employee site address",
            org_employee_portal_not_configured: "Employee portal URL is not configured.",
            org_open_link: "Open link",
            org_cloud_link: "Cloud connection",
            org_cloud_link_text: "Optional beta add-on. Upload this local organization only when you want employee portal access or migration testing.",
            org_cloud_api: "Cloud API",
            org_cloud_email: "Cloud owner email",
            org_cloud_password: "Cloud owner password",
            org_cloud_replace: "Replace scheduling data in the selected cloud organization",
            org_cloud_upload: "Upload and link cloud organization",
            org_cloud_unlink: "Disconnect cloud portal",
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
            preferences_select_employee: "Select employee",
            org_no_employee_link: "No employee link",
            org_member_employee_not_linked: "Not linked",
            org_no_members: "No members found.",
            org_no_invitations: "No invitations found.",
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
            org_msg_invitation_copied: "Invitation link copied.",
            org_msg_no_active_organization: "Current user has no active organization.",
            org_msg_creating_invitation: "Creating invitation...",
            org_msg_select_employee_first: "Select an employee before creating an employee invitation.",
            org_msg_invitation_created: "Invitation created.",
            org_msg_invitation_email_sent: "Invitation emailed.",
            org_msg_invitation_email_failed: "Invitation created, but email delivery failed. Copy the link and send it manually.",
            org_msg_invitation_email_disabled: "Invitation created. Email delivery is not configured, so copy the link and send it manually.",
            org_msg_updating_role: "Updating role...",
            org_msg_role_updated: "Role updated.",
            org_msg_updating_employee_link: "Updating employee link...",
            org_msg_employee_link_updated: "Employee link updated.",
            org_msg_saving_profile: "Saving profile...",
            org_msg_profile_saved: "Profile saved.",
            org_msg_changing_password: "Changing password...",
            org_msg_password_changed: "Password changed.",
            org_no_organization: "No organization",
            org_role_owner: "Owner",
            org_role_admin: "Admin",
            org_role_manager: "Manager",
            org_role_scheduler: "Scheduler",
            org_role_read_only: "Observer",
            org_role_employee: "Employee",
            org_role_hint_owner: "Owner has full access and can manage other owners and admins.",
            org_role_hint_admin: "Admin can manage schedules, employees, invitations, and most organization settings.",
            org_role_hint_scheduler: "Scheduler can edit schedules and employee setup but cannot manage owners.",
            org_role_hint_manager: "Manager can view schedule workflows and weekly preferences without schedule editing.",
            org_role_hint_read_only: "Observer can view schedules and organization information without editing.",
            org_role_hint_employee: "Employee access requires linking this account to an employee record.",
            org_status_active: "Active",
            org_status_disabled: "Disabled",
            org_status_invited: "Invited",
            org_status_pending: "Pending",
            org_status_accepted: "Accepted",
            org_status_expired: "Expired",
            org_status_revoked: "Revoked",
            org_cloud_not_connected: "Cloud portal is optional and is not connected for this local organization.",
            org_cloud_only_admin_connect: "Only owners and admins can connect this organization to cloud.",
            org_cloud_enter_valid_url: "Enter a valid Cloud API URL.",
            org_cloud_preparing_export: "Preparing local organization export...",
            org_cloud_signing_in: "Signing in to Cloud beta API...",
            org_cloud_owner_required: "Cloud account must be an owner or admin of the target organization.",
            org_cloud_uploading: "Uploading local organization to cloud...",
            org_cloud_saving_link: "Saving cloud link locally...",
            org_cloud_linked_imported: "Linked. Imported {employees} employees, {positions} positions, {shift_templates} shift templates.",
            org_cloud_only_admin_disconnect: "Only owners and admins can disconnect the cloud portal.",
            org_cloud_disconnecting: "Disconnecting cloud portal...",
            org_cloud_disconnected: "Cloud portal disconnected for this local organization.",
            common_yes: "Yes",
            common_no: "No",
            common_delete: "Delete",
        },
        ru: {
            app_title: "ShiftCare",
            auth_kicker: "Desktop first",
            auth_login: "Войти",
            auth_authorize_user: "Авторизовать пользователя",
            auth_employee_login: "Вход сотрудника",
            auth_add_organization: "Добавить организацию",
            auth_login_action_text: "Загрузить данные организации на этот компьютер",
            auth_employee_login_action_text: "Открыть пожелания и расписание только для просмотра",
            auth_add_organization_text: "Создать облачную организацию и начать локально",
            auth_employee_portal: "Портал сотрудника",
            auth_login_method: "Способ входа",
            auth_id_card: "Номер ID",
            auth_id_card_placeholder: "Например: 123456789",
            auth_email_placeholder: "name@example.com",
            auth_create_organization: "Создать организацию",
            auth_initial_role: "Ваша роль",
            auth_initial_role_hint: "Первый аккаунт всегда становится владельцем организации.",
            auth_msg_cloud_unreachable: "Облако недоступно. Проверьте интернет и попробуйте ещё раз.",
            auth_msg_desktop_ready: "Авторизуйте облачного пользователя или добавьте новую организацию. Работа продолжится локально на этом компьютере.",
            auth_msg_employee_portal_ready: "Портал сотрудников готов.",
            auth_msg_employee_login_ready: "Портал сотрудников готов. Войдите через аккаунт сотрудника.",
            auth_msg_status_check_failed: "Не удалось проверить состояние авторизации",
            auth_msg_signing_in: "Вход...",
            auth_msg_signing_in_desktop: "Вход и загрузка данных организации...",
            auth_msg_login_success: "Вход выполнен.",
            auth_msg_org_setup_desktop_only: "Создание организации доступно только в desktop-приложении.",
            auth_msg_creating_org: "Создание организации...",
            auth_msg_creating_org_desktop: "Создание облачной организации и загрузка локально...",
            auth_msg_org_created: "Организация создана.",
            auth_create_owner: "Создать владельца",
            auth_email: "Email",
            auth_password: "Пароль",
            auth_org_access: "Доступ к организации",
            auth_org_name: "Название организации",
            auth_your_name: "Ваше имя",
            auth_create_owner_account: "Создать аккаунт владельца",
            auth_foundation: "Локальное рабочее пространство расписаний",
            auth_foundation_text: "Войдите через облачный аккаунт, загрузите данные организации на этот компьютер и продолжайте работать с расписанием локально без ожидания сети.",
            auth_connection: "Подключение",
            auth_local_recovery: "Синхронизация",
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
            org_invite: "Пригласить участника",
            org_invite_text: "Отправьте одноразовую ссылку приглашения по email и выберите роль доступа.",
            org_role: "Роль",
            org_expires: "Действует дней",
            org_create_invitation: "Создать приглашение",
            org_employee_portal: "Портал сотрудников",
            org_employee_portal_text: "Публичная страница входа сотрудников для пожеланий и просмотра расписания.",
            org_employee_site_address: "Адрес сайта для сотрудников",
            org_employee_portal_not_configured: "Адрес портала сотрудников не настроен.",
            org_open_link: "Открыть ссылку",
            org_cloud_link: "Подключение к облаку",
            org_cloud_link_text: "Необязательное beta-дополнение. Загружайте локальную организацию только для портала сотрудников или тестирования миграции.",
            org_cloud_api: "Cloud API",
            org_cloud_email: "Email владельца в облаке",
            org_cloud_password: "Пароль владельца в облаке",
            org_cloud_replace: "Заменить данные расписания в выбранной облачной организации",
            org_cloud_upload: "Загрузить и привязать облачную организацию",
            org_cloud_unlink: "Отключить облачный портал",
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
            preferences_select_employee: "Выберите сотрудника",
            org_no_employee_link: "Без привязки к сотруднику",
            org_member_employee_not_linked: "Не привязан",
            org_no_members: "Участники не найдены.",
            org_no_invitations: "Приглашения не найдены.",
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
            org_msg_invitation_copied: "Ссылка приглашения скопирована.",
            org_msg_no_active_organization: "У текущего пользователя нет активной организации.",
            org_msg_creating_invitation: "Создание приглашения...",
            org_msg_select_employee_first: "Сначала выберите сотрудника для приглашения.",
            org_msg_invitation_created: "Приглашение создано.",
            org_msg_invitation_email_sent: "Приглашение отправлено по email.",
            org_msg_invitation_email_failed: "Приглашение создано, но письмо не отправилось. Скопируйте ссылку и отправьте её вручную.",
            org_msg_invitation_email_disabled: "Приглашение создано. Email-отправка не настроена, поэтому скопируйте ссылку и отправьте её вручную.",
            org_msg_updating_role: "Обновление роли...",
            org_msg_role_updated: "Роль обновлена.",
            org_msg_updating_employee_link: "Обновление привязки сотрудника...",
            org_msg_employee_link_updated: "Привязка сотрудника обновлена.",
            org_msg_saving_profile: "Сохранение профиля...",
            org_msg_profile_saved: "Профиль сохранён.",
            org_msg_changing_password: "Смена пароля...",
            org_msg_password_changed: "Пароль изменён.",
            org_no_organization: "Нет организации",
            org_role_owner: "Владелец",
            org_role_admin: "Администратор",
            org_role_manager: "Менеджер",
            org_role_scheduler: "Планировщик",
            org_role_read_only: "Наблюдатель",
            org_role_employee: "Сотрудник",
            org_role_hint_owner: "Владелец имеет полный доступ и управляет другими владельцами и администраторами.",
            org_role_hint_admin: "Администратор управляет расписанием, сотрудниками, приглашениями и большинством настроек организации.",
            org_role_hint_scheduler: "Планировщик редактирует расписание и настройки сотрудников, но не управляет владельцами.",
            org_role_hint_manager: "Менеджер видит рабочие процессы расписания и пожелания без права редактирования расписания.",
            org_role_hint_read_only: "Наблюдатель просматривает расписания и данные организации без редактирования.",
            org_role_hint_employee: "Доступ сотрудника требует привязки аккаунта к записи сотрудника.",
            org_status_active: "Активен",
            org_status_disabled: "Отключён",
            org_status_invited: "Приглашён",
            org_status_pending: "Ожидает",
            org_status_accepted: "Принято",
            org_status_expired: "Истекло",
            org_status_revoked: "Отозвано",
            org_cloud_not_connected: "Облачный портал необязателен и не подключён для этой локальной организации.",
            org_cloud_only_admin_connect: "Только владелец или администратор может подключить организацию к облаку.",
            org_cloud_enter_valid_url: "Введите корректный Cloud API URL.",
            org_cloud_preparing_export: "Подготовка экспорта локальной организации...",
            org_cloud_signing_in: "Вход в Cloud beta API...",
            org_cloud_owner_required: "Облачный аккаунт должен быть владельцем или администратором целевой организации.",
            org_cloud_uploading: "Загрузка локальной организации в облако...",
            org_cloud_saving_link: "Сохранение облачной привязки локально...",
            org_cloud_linked_imported: "Привязано. Импортировано: сотрудники {employees}, должности {positions}, шаблоны смен {shift_templates}.",
            org_cloud_only_admin_disconnect: "Только владелец или администратор может отключить облачный портал.",
            org_cloud_disconnecting: "Отключение облачного портала...",
            org_cloud_disconnected: "Облачный портал отключён для этой локальной организации.",
            common_yes: "Да",
            common_no: "Нет",
            common_delete: "Удалить",
        },
        he: {
            app_title: "ShiftCare",
            auth_kicker: "Desktop first",
            auth_login: "כניסה",
            auth_authorize_user: "אישור משתמש",
            auth_employee_login: "כניסת עובד",
            auth_add_organization: "הוספת ארגון",
            auth_login_action_text: "טען את נתוני הארגון למחשב הזה",
            auth_employee_login_action_text: "פתח בקשות שבועיות וסידור לצפייה בלבד",
            auth_add_organization_text: "צור ארגון בענן והתחל מקומית",
            auth_employee_portal: "פורטל עובדים",
            auth_login_method: "שיטת כניסה",
            auth_id_card: "מספר תעודה",
            auth_id_card_placeholder: "לדוגמה: 123456789",
            auth_email_placeholder: "name@example.com",
            auth_create_organization: "צור ארגון",
            auth_initial_role: "התפקיד שלך",
            auth_initial_role_hint: "החשבון הראשון הוא תמיד בעלים של הארגון.",
            auth_msg_cloud_unreachable: "הענן אינו זמין. בדוק את החיבור לאינטרנט ונסה שוב.",
            auth_msg_desktop_ready: "אשר משתמש ענן או הוסף ארגון חדש. העבודה תמשיך מקומית במחשב הזה.",
            auth_msg_employee_portal_ready: "פורטל העובדים מוכן.",
            auth_msg_employee_login_ready: "פורטל העובדים מוכן. היכנס עם חשבון העובד שלך.",
            auth_msg_status_check_failed: "לא ניתן לבדוק את מצב ההרשאה",
            auth_msg_signing_in: "מתחבר...",
            auth_msg_signing_in_desktop: "מתחבר וטוען את נתוני הארגון...",
            auth_msg_login_success: "הכניסה הצליחה.",
            auth_msg_org_setup_desktop_only: "הקמת ארגון זמינה רק באפליקציית הדסקטופ.",
            auth_msg_creating_org: "יוצר ארגון...",
            auth_msg_creating_org_desktop: "יוצר ארגון בענן וטוען אותו מקומית...",
            auth_msg_org_created: "הארגון נוצר.",
            auth_create_owner: "יצירת בעלים ראשון",
            auth_email: "אימייל",
            auth_password: "סיסמה",
            auth_org_access: "גישה לארגון",
            auth_org_name: "שם הארגון",
            auth_your_name: "השם שלך",
            auth_create_owner_account: "צור חשבון בעלים",
            auth_foundation: "סביבת תזמון מקומית",
            auth_foundation_text: "היכנס עם חשבון הענן, טען את נתוני הארגון למחשב הזה והמשך לעבוד מקומית בלי להמתין לרשת.",
            auth_connection: "חיבור",
            auth_local_recovery: "סנכרון ענן",
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
            org_invite: "הזמן חבר",
            org_invite_text: "שלח קישור הזמנה חד-פעמי באימייל ובחר תפקיד גישה.",
            org_role: "תפקיד",
            org_expires: "תוקף בימים",
            org_create_invitation: "צור הזמנה",
            org_employee_portal: "פורטל עובדים",
            org_employee_portal_text: "עמוד כניסה ציבורי לעובדים עבור בקשות שבועיות וצפייה בסידור.",
            org_employee_site_address: "כתובת אתר לעובדים",
            org_employee_portal_not_configured: "כתובת פורטל העובדים לא הוגדרה.",
            org_open_link: "פתח קישור",
            org_cloud_link: "חיבור לענן",
            org_cloud_link_text: "תוסף בטא אופציונלי. העלה את הארגון המקומי רק עבור פורטל עובדים או בדיקות מיגרציה.",
            org_cloud_api: "Cloud API",
            org_cloud_email: "אימייל בעלים בענן",
            org_cloud_password: "סיסמת בעלים בענן",
            org_cloud_replace: "החלף נתוני סידור בארגון הענן שנבחר",
            org_cloud_upload: "העלה וקשר ארגון ענן",
            org_cloud_unlink: "נתק פורטל ענן",
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
            preferences_select_employee: "בחר עובד",
            org_no_employee_link: "ללא קישור לעובד",
            org_member_employee_not_linked: "לא מקושר",
            org_no_members: "לא נמצאו חברים.",
            org_no_invitations: "לא נמצאו הזמנות.",
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
            org_msg_invitation_copied: "קישור ההזמנה הועתק.",
            org_msg_no_active_organization: "למשתמש הנוכחי אין ארגון פעיל.",
            org_msg_creating_invitation: "יוצר הזמנה...",
            org_msg_select_employee_first: "יש לבחור עובד לפני יצירת הזמנה.",
            org_msg_invitation_created: "ההזמנה נוצרה.",
            org_msg_invitation_email_sent: "ההזמנה נשלחה באימייל.",
            org_msg_invitation_email_failed: "ההזמנה נוצרה, אך שליחת האימייל נכשלה. העתק את הקישור ושלח אותו ידנית.",
            org_msg_invitation_email_disabled: "ההזמנה נוצרה. שליחת אימייל לא מוגדרת, לכן העתק את הקישור ושלח אותו ידנית.",
            org_msg_updating_role: "מעדכן תפקיד...",
            org_msg_role_updated: "התפקיד עודכן.",
            org_msg_updating_employee_link: "מעדכן קישור לעובד...",
            org_msg_employee_link_updated: "הקישור לעובד עודכן.",
            org_msg_saving_profile: "שומר פרופיל...",
            org_msg_profile_saved: "הפרופיל נשמר.",
            org_msg_changing_password: "משנה סיסמה...",
            org_msg_password_changed: "הסיסמה שונתה.",
            org_no_organization: "אין ארגון",
            org_role_owner: "בעלים",
            org_role_admin: "אדמין",
            org_role_manager: "מנהל",
            org_role_scheduler: "מתזמן",
            org_role_read_only: "צופה",
            org_role_employee: "עובד",
            org_role_hint_owner: "לבעלים יש גישה מלאה וניהול של בעלים ואדמינים אחרים.",
            org_role_hint_admin: "אדמין מנהל סידורים, עובדים, הזמנות ורוב הגדרות הארגון.",
            org_role_hint_scheduler: "מתזמן יכול לערוך סידורים והגדרות עובדים, אך לא לנהל בעלים.",
            org_role_hint_manager: "מנהל יכול לצפות בתהליכי סידור ובבקשות שבועיות ללא עריכת סידור.",
            org_role_hint_read_only: "צופה יכול לראות סידורים ופרטי ארגון ללא עריכה.",
            org_role_hint_employee: "גישת עובד דורשת קישור החשבון לרשומת עובד.",
            org_status_active: "פעיל",
            org_status_disabled: "מושבת",
            org_status_invited: "הוזמן",
            org_status_pending: "ממתין",
            org_status_accepted: "התקבל",
            org_status_expired: "פג תוקף",
            org_status_revoked: "בוטל",
            org_cloud_not_connected: "פורטל הענן אופציונלי ואינו מחובר לארגון המקומי הזה.",
            org_cloud_only_admin_connect: "רק בעלים או אדמין יכולים לחבר את הארגון לענן.",
            org_cloud_enter_valid_url: "הזן Cloud API URL תקין.",
            org_cloud_preparing_export: "מכין ייצוא ארגון מקומי...",
            org_cloud_signing_in: "מתחבר ל-Cloud beta API...",
            org_cloud_owner_required: "חשבון הענן חייב להיות בעלים או אדמין בארגון היעד.",
            org_cloud_uploading: "מעלה את הארגון המקומי לענן...",
            org_cloud_saving_link: "שומר קישור ענן מקומית...",
            org_cloud_linked_imported: "קושר. יובאו {employees} עובדים, {positions} תפקידים, {shift_templates} תבניות משמרת.",
            org_cloud_only_admin_disconnect: "רק בעלים או אדמין יכולים לנתק את פורטל הענן.",
            org_cloud_disconnecting: "מנתק פורטל ענן...",
            org_cloud_disconnected: "פורטל הענן נותק עבור הארגון המקומי הזה.",
            common_yes: "כן",
            common_no: "לא",
            common_delete: "מחיקה",
        },
    };

    function language() {
        return localStorage.getItem("scheduleAppLanguage") || document.documentElement.lang || "en";
    }

    function getAppName() {
        return document.body?.dataset?.appName || "ShiftCare";
    }

    function t(key) {
        const lang = language();
        if (key === "app_title") {
            return getAppName();
        }
        return (translations[lang] || translations.en)[key] || translations.en[key] || key;
    }

    function hasAuthTranslation(key) {
        const lang = language();
        return Boolean((translations[lang] || translations.en)[key] || translations.en[key]);
    }

    function setText(selector, key) {
        document.querySelectorAll(selector).forEach((element) => {
            element.textContent = t(key);
        });
    }

    function applyDataTranslations() {
        document.querySelectorAll("[data-i18n]").forEach((element) => {
            const key = element.dataset.i18n;
            if (hasAuthTranslation(key)) {
                element.textContent = t(key);
            }
        });
    }

    function applyAuthTranslations() {
        const isAcceptInvitation = Boolean(document.getElementById("accept-title"));
        const isLoginShell = Boolean(document.getElementById("login-modal"));
        const isCloudEmployeePortal = Boolean(window.scheduleAuth?.isHostedCloudOrigin?.());

        setText("#auth-title", "app_title");
        setText(".brand-subtitle", "org_title");
        setText(".auth-brand p", isAcceptInvitation
            ? "auth_create_account"
            : (isLoginShell ? (isCloudEmployeePortal ? "auth_employee_portal" : "auth_foundation") : "auth_org_access"));
        if (isCloudEmployeePortal) {
            setText("#open-login-modal .auth-portal-button-title", "auth_employee_login");
            setText("#open-login-modal .auth-portal-button-text", "auth_employee_login_action_text");
        } else {
            setText("#open-login-modal strong", "auth_authorize_user");
            setText("#open-login-modal span", "auth_login_action_text");
        }
        setText("#open-organization-modal strong", "auth_add_organization");
        setText("#open-organization-modal span", "auth_add_organization_text");
        setText("#login-modal-title", isCloudEmployeePortal ? "auth_employee_login" : "auth_authorize_user");
        setText("#organization-modal-title", "auth_add_organization");
        setText("#login-method-email", "auth_email");
        setText("#login-method-id-card", "auth_id_card");
        document.querySelector(".auth-login-methods")?.setAttribute("aria-label", t("auth_login_method"));
        setText("#login-tab", "auth_login");
        setText("#bootstrap-tab", "auth_create_owner");
        setText('label[for="login-email"], #login-form label:nth-of-type(1) span, #bootstrap-form label:nth-of-type(3) span', "auth_email");
        setText('#login-form label:nth-of-type(2) span, #bootstrap-form label:nth-of-type(5) span, #accept-form label:nth-of-type(3) span', "auth_password");
        setText("#login-form .auth-submit", "auth_login");
        setText("#bootstrap-form label:nth-of-type(1) span", "auth_org_name");
        setText("#bootstrap-form label:nth-of-type(2) span, #accept-form label:nth-of-type(2) span", "auth_your_name");
        setText("#bootstrap-form label:nth-of-type(4) span", "auth_initial_role");
        setText("#bootstrap-form label:nth-of-type(4) .field-hint", "auth_initial_role_hint");
        setText("#bootstrap-form .auth-submit", "auth_create_organization");
        setText(".auth-side h2", isAcceptInvitation ? "auth_join_org" : "auth_foundation");
        setText(".auth-side-content > p:not(.auth-kicker):not(.api-mode-status):not(.api-mode-title)", isAcceptInvitation ? "auth_join_text" : "auth_foundation_text");
        setText("#accept-title", "auth_accept_title");
        setText("#accept-form label:nth-of-type(1) span", "auth_invitation_token");
        setText("#accept-form .auth-submit", "auth_accept_button");
        setText(".auth-kicker", isAcceptInvitation ? "auth_employee_access" : "auth_kicker");
        setText("#organization-title", "org_title");
        setText(".page-subtitle", "org_subtitle");
        setText("#logout-btn", "common_logout");
        setText(".nav-item[href='/'] .nav-label", "nav_home");
        setText(".nav-item[href='/schedule'] .nav-label", "nav_schedule");
        setText(".nav-item[href='/organization'] .nav-label", "org_title");
        setText(".nav-item[href='/settings'] .nav-label", "nav_settings");
        setText("#organization-selector-wrap span", "org_selector");
        setText(".organization-panel:first-of-type .settings-section-title", "org_account");
        setText(".organization-panel:first-of-type .settings-section-text", "org_account_text");
        setText("#profile-form label:nth-of-type(1) span", "org_full_name");
        setText("#profile-form label:nth-of-type(2) span", "auth_email");
        setText("#profile-form .btn", "org_save_profile");
        setText("#password-form label:nth-of-type(1) span", "org_current_password");
        setText("#password-form label:nth-of-type(2) span", "org_new_password");
        setText("#password-form .btn", "org_change_password");
        setText("#invite-form .settings-section-title", "org_invite");
        setText("#invite-form .settings-section-text", "org_invite_text");
        setText("#invite-form label:nth-of-type(1) span", "org_role");
        setText("#invite-form label:nth-of-type(2) span", "org_employee");
        setText("#invite-form label:nth-of-type(3) span", "auth_email");
        setText("#invite-form label:nth-of-type(4) span", "org_expires");
        setText("#invite-form > .btn", "org_create_invitation");
        setText("#employee-portal-panel .settings-section-title", "org_employee_portal");
        setText("#employee-portal-panel .settings-section-text", "org_employee_portal_text");
        setText("#employee-portal-panel label span", "org_employee_site_address");
        setText("#open-employee-portal-link", "org_open_link");
        setText("#copy-employee-portal-btn", "org_copy_link");
        setText("#cloud-link-panel .settings-section-title", "org_cloud_link");
        setText("#cloud-link-panel .settings-section-text", "org_cloud_link_text");
        setText('label[for="cloud-api-base-url"] span, #cloud-link-form label:nth-of-type(1) span', "org_cloud_api");
        setText("#cloud-link-form label:nth-of-type(2) span", "org_cloud_email");
        setText("#cloud-link-form label:nth-of-type(3) span", "org_cloud_password");
        setText("#cloud-link-form .checkbox-row span", "org_cloud_replace");
        setText("#cloud-link-form > .btn", "org_cloud_upload");
        setText("#cloud-unlink-btn", "org_cloud_unlink");
        setText("#cloud-link-summary dt:nth-of-type(1)", "org_cloud_linked_api");
        setText("#cloud-link-summary div:nth-child(1) dt", "org_cloud_linked_api");
        setText("#cloud-link-summary div:nth-child(2) dt", "org_cloud_linked_org");
        setText("#cloud-link-summary div:nth-child(3) dt", "org_cloud_linked_at");
        setText("#invite-result-wrap label span", "org_invitation_link");
        setText("#open-invite-link", "org_open_link");
        setText("#copy-invite-btn", "org_copy_link");
        setText("#members-panel .settings-section-title", "org_members");
        setText("#members-panel .settings-section-text", "org_members_text");
        setText("#invitations-panel .settings-section-title", "org_invitations");
        setText("#invitations-panel .settings-section-text", "org_invitations_text");
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
        applyDataTranslations();
    }

    window.organizationAuthText = t;

    document.addEventListener("DOMContentLoaded", applyAuthTranslations);
    document.addEventListener("app-language-changed", applyAuthTranslations);
})();
