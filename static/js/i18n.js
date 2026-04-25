window.escapeHtml = window.escapeHtml || function (value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
};

const I18N_TRANSLATIONS = {
    en: {
        app_title: "Schedule App",
        app_subtitle: "Nursing staff scheduling",

        nav_section_main: "Main",
        nav_dashboard: "Dashboard",
        nav_schedule: "Schedule",
        nav_employees: "Employees",
        nav_requests: "Preferences",
        nav_settings: "Settings",

        sidebar_footer_title: "Version 0.13.3_beta",
        sidebar_footer_text: "Interface redesign in progress. The current goal is a simpler and clearer workflow.",

        page_title: "Dashboard",
        page_subtitle: "A cleaner and more understandable control center for weekly scheduling.",

        home_title: "Main Menu",
        home_subtitle: "Choose the action you need right now.",

        home_schedule_title: "Create schedule",
        home_schedule_text: "Open the weekly schedule and create or edit shifts.",

        home_employees_title: "Employees",
        home_employees_text: "Add, edit, and manage employees.",

        home_requests_title: "Preferences",
        home_requests_text: "Review weekly preferences, days off, and restrictions.",

        home_settings_title: "Settings",
        home_settings_text: "Configure positions, templates, and system data.",

        toggle_sidebar: "Toggle menu",

        lang_he: "עברית",
        lang_en: "English",
        lang_ru: "Русский",

        hero_title: "Weekly scheduling, without interface chaos",
        hero_text: "This version focuses on clarity, speed, and a more minimal working experience for daily use.",
        hero_open_schedule: "Open schedule",
        hero_manage_employees: "Manage employees",
        hero_system_settings: "System settings",

        stats_title: "This week",
        stat_morning: "Morning coverage",
        stat_evening: "Evening coverage",
        stat_night: "Night coverage",
        stat_morning_value: "93%",
        stat_evening_value: "88%",
        stat_night_value: "100%",
        stat_morning_note: "Almost complete",
        stat_evening_note: "Needs attention",
        stat_night_note: "Fully covered",

        footer_docs: "Documentation",
        footer_guide: "User Guide",
        footer_version: "Schedule App v0.13.3_beta",

        quick_actions_title: "Quick actions",
        quick_action_schedule_title: "Open current week",
        quick_action_schedule_text: "Go directly to the weekly schedule and continue editing.",
        quick_action_generate_title: "Auto-generate schedule",
        quick_action_generate_text: "Run the algorithm and fill remaining shifts faster.",
        quick_action_export_title: "Export Excel",
        quick_action_export_text: "Prepare the weekly schedule for printing and sharing.",
        quick_action_requests_title: "Employee requests",
        quick_action_requests_text: "Review preferences, days off, vacations, and restrictions.",

        alerts_title: "Warnings and notes",
        alert_1_title: "Tuesday morning",
        alert_1_text: "One more employee is still needed to complete coverage.",
        alert_2_title: "Wednesday evening",
        alert_2_text: "Minimum female staff requirement is not fully met.",
        alert_3_title: "Friday night",
        alert_3_text: "Night shift is complete and does not require changes.",

        summary_title: "Current workspace",
        summary_week: "Selected week",
        summary_position: "Selected position",
        summary_language: "Interface language",
        summary_status: "Redesign status",
        summary_status_value: "Foundation ready",

        summary_badge: "RTL supported for Hebrew",
        schedule_page_title: "Schedule",
        schedule_page_subtitle: "Manage the weekly schedule, generate shifts, and export the result.",

        schedule_week_start: "Week start",
        schedule_position: "Position",
        schedule_select_position: "Select position",

        schedule_load_btn: "Load",
        schedule_generate_btn: "Auto generate",
        schedule_generate_all_btn: "Auto generate all",
        schedule_generating_title: "Generating schedule",
        schedule_generating_text: "The algorithm is checking coverage, rest rules, and employee limits.",
        schedule_clear_btn: "Clear week",
        schedule_export_btn: "Export Excel",
        schedule_clear_message_btn: "Clear message",
        schedule_toolbar_generate: "Generate",
        schedule_toolbar_output: "Output",
        schedule_toolbar_danger: "Danger zone",
        schedule_status_legend: "Status",
        schedule_status_week: "Week",
        schedule_status_position: "Position",
        schedule_status_staff: "Staff",
        schedule_status_shifts: "Shifts",
        schedule_status_gaps: "gaps",

        schedule_initial_hint: "Select a week and a position, then load the schedule.",

        schedule_add_shift: "Add shift",
        schedule_select_shift_template: "Select shift template",
        schedule_add_shift_btn: "Add shift",

        schedule_day_status: "Day status",
        schedule_no_status: "No status",
        schedule_save_status_btn: "Save status",

        schedule_manual_day_status: "Manual day status",
        schedule_no_shifts_assigned: "No shifts assigned",
        schedule_other_positions_label: "Other positions",
        schedule_delete_shift_btn: "Delete",
        schedule_remove_status: "Remove status",
        schedule_shift_status: "Shift status",
        schedule_status_sick_hint: "Blocks the whole day cell",
        schedule_status_day_off_hint: "Marks the whole day as a day off",
        schedule_no_shifts_for_no_show: "No shifts available for no-show status",

        schedule_employee_header: "Employee",
        schedule_coverage_header: "Coverage",
        schedule_no_employees_for_position: "No employees are assigned to this position.",

        employee_min_target_max: "Min/Target/Max",

        shift_morning: "Morning",
        shift_evening: "Evening",
        shift_night: "Night",

        status_sick: "Sick",
        status_day_off: "Day off",
        status_no_show: "No-show",

        coverage_staff: "Staff",
        coverage_women: "Women",
        coverage_men: "Men",
        coverage_intervals_short: "slots",

        weekday_sunday: "Sunday",
        weekday_monday: "Monday",
        weekday_tuesday: "Tuesday",
        weekday_wednesday: "Wednesday",
        weekday_thursday: "Thursday",
        weekday_friday: "Friday",
        weekday_saturday: "Saturday",

        msg_failed_load_positions: "Failed to load positions.",
        msg_server_error_load_positions: "Server error while loading positions.",

        msg_select_week_start: "Please select a week start date.",
        msg_select_position: "Please select a position.",

        msg_failed_load_schedule_data: "Failed to load schedule data.",
        msg_server_error_load_schedule: "Server error while loading schedule.",
        msg_schedule_loaded: "Schedule loaded successfully.",
        msg_failed_save_schedule_display: "Failed to save coverage display mode.",

        msg_auto_generate_failed: "Auto-generation failed.",
        msg_auto_generate_done: "Auto-generation finished.",
        schedule_generate_all_done: "Auto-generation for all positions finished.",
        schedule_generate_all_success_summary: "Generated positions",
        schedule_generate_all_created_summary: "Created shifts",
        schedule_generate_all_failures_prefix: "Failed positions",
        msg_created_count: "Created",
        msg_optimization_moved: "Optimized moves",
        msg_warnings: "Warnings",
        msg_server_error_auto_generate: "Server error while auto-generating schedule.",
        generation_summary_title: "Generation summary",
        generation_summary_subtitle: "The latest auto-generation result for the selected week and position.",
        generation_summary_clear_btn: "Clear summary",
        generation_summary_open_panel: "Detailed generation results are shown in the summary panel.",
        generation_created_note: "New schedule entries added by auto-generation.",
        generation_optimized_note: "Existing generated entries reassigned for a better balance.",
        generation_day_off_count: "Generated day off",
        generation_day_off_note: "Automatic day-off statuses created for uncovered employee days.",
        generation_hard_note: "Blocking issues found by the pre-check.",
        generation_soft_note: "Warnings that still allowed generation to continue.",
        generation_unfilled_note: "Coverage gaps that remained after generation.",
        generation_run_overview: "Run overview",
        generation_summary_week: "Week",
        generation_summary_position: "Position",
        generation_summary_status: "Feasibility status",
        generation_feasibility_status_ok: "OK",
        generation_feasibility_status_blocking: "Blocking",
        generation_unfilled_title: "Remaining unfilled requirements",
        generation_summary_clean_title: "Clean generation result",
        generation_summary_clean_text: "The run finished without warnings, hard blockers, or remaining uncovered requirements.",
        generation_missing_total: "Missing total",
        generation_missing_female: "Missing female",
        generation_missing_male: "Missing male",
        generation_reasons: "Reasons",

        msg_confirm_clear_week: "Are you sure you want to delete the schedule for this week and this position?",
        msg_confirm_clear_week_title: "Clear week schedule",
        msg_failed_clear_week: "Failed to clear week schedule.",
        msg_week_cleared: "Week schedule cleared.",
        msg_deleted_count: "Deleted",
        confirm_impact_position: "Position",
        confirm_impact_employee: "Employee",
        confirm_impact_template: "Template",
        confirm_impact_assignment: "Assignment",
        confirm_impact_week: "Week",
        confirm_impact_schedule_entries: "Schedule entries",
        confirm_impact_assignments: "Assignments",
        confirm_impact_general_preferences: "General preferences",
        confirm_impact_weekly_preferences: "Weekly preferences",
        confirm_impact_day_statuses: "Day statuses",
        confirm_impact_day_off_statuses: "Day-off statuses",
        confirm_impact_shift_requirements: "Shift requirements",
        confirm_impact_coverage_requirements: "Coverage requirements",
        confirm_impact_assigned_employees: "Assigned employees",
        confirm_impact_in_use_warning: "This template is still used in the schedule and deletion will be blocked.",
        confirm_impact_fetch_failed: "Could not load related records. Review carefully before deleting.",
        msg_server_error_clear_week: "Server error while clearing week schedule.",

        msg_select_shift_template_first: "Please select a shift template first.",
        msg_status_selector_not_found: "Status selector not found.",

        msg_failed_add_shift: "Failed to add shift.",
        msg_shift_added: "Shift added successfully.",
        msg_server_error_add_shift: "Server error while adding shift.",

        msg_failed_delete_shift: "Failed to delete shift.",
        msg_shift_deleted: "Shift deleted successfully.",
        msg_server_error_delete_shift: "Server error while deleting shift.",

        msg_failed_save_day_status: "Failed to save day status.",
        msg_day_status_saved: "Day status saved successfully.",
        msg_server_error_save_day_status: "Server error while saving day status.",
        msg_failed_save_shift_status: "Failed to save shift status.",
        msg_no_show_saved: "No-show status saved successfully.",
        msg_no_show_removed: "No-show status removed successfully.",
        msg_server_error_save_shift_status: "Server error while saving shift status.",

        generation_warning_no_active_slots_week: "No active coverage slots for this week",
        generation_warning_no_active_slots_day: "No active coverage slots for this day",
        generation_warning_emergency_fatigue: "emergency fatigue relaxation was used to cover a slot",
        generation_warning_underfilled: "underfilled",
        generation_warning_reasons: "Reasons:",
        generation_warning_worked_days: "has worked days without a mandatory weekly day off",
        generation_warning_consecutive_nights: "consecutive night days",
        generation_warning_consecutive_splits: "consecutive split days",
        generation_reason_not_enough_female: "not enough female employees available",
        generation_reason_not_enough_male: "not enough male employees available",
        generation_reason_split_pair: "split-only template has no valid pair",
        generation_reason_day_status: "day status blocks employee",
        generation_reason_not_assigned: "employee is not assigned to this position",
        generation_reason_max_shifts: "employee reached max shifts",
        generation_reason_weekly_max_shifts: "employee reached weekly maximum shifts",
        generation_reason_preference_or_permission: "employee preferences or permissions block this shift",
        generation_reason_mandatory_day_off: "mandatory weekly day off would be violated",
        generation_reason_overlapping_shift: "employee already has an overlapping shift",
        generation_reason_cannot_split_day: "employee cannot work morning and evening on the same day",
        generation_reason_unpairable_shift_type: "employee already has another shift type that cannot be paired",
        generation_reason_split_only_combo: "morning-evening combo requires split-only templates",
        generation_reason_weekly_preference_split: "weekly preference blocks morning-evening combo",
        generation_reason_two_shifts_day: "employee already has two shifts that day",
        generation_reason_off_or_vacation: "employee requested off or vacation",
        generation_reason_preference_conflict: "shift conflicts with employee preference",
        generation_reason_morning_after_night: "morning after night is forbidden",
        generation_reason_night_evening_rest: "not enough rest after night before evening",
        generation_reason_morning_evening_rest: "not enough rest between morning and evening",
        generation_reason_weekly_day_off: "weekly day off would be violated",
        generation_reason_consecutive_nights: "consecutive night limit reached",
        generation_reason_consecutive_splits: "consecutive split limit reached",
        generation_reason_too_many_consecutive_nights: "too many consecutive night shifts",
        generation_reason_too_many_consecutive_splits: "too many consecutive split shifts",
        generation_reason_no_coverage_gain: "candidates existed, but they did not improve coverage without overfilling other intervals",
        generation_precheck_blocking: "Pre-check blocking:",
        generation_precheck_warning: "Pre-check warning:",
        generation_precheck_no_slots: "No active coverage slots can be built from coverage requirements.",
        generation_precheck_no_template: "No active shift template covers this required interval.",
        generation_precheck_no_legacy_template: "No active non-split template exists for this legacy shift requirement.",
        generation_precheck_staff_shortage: "Required staff is greater than employees assigned to the position.",
        generation_precheck_female_shortage: "Required female staff is greater than available female employees.",
        generation_precheck_male_shortage: "Required male staff is greater than available male employees.",
        generation_precheck_no_candidate: "No eligible employee/template candidate can cover this interval.",
        generation_precheck_emergency_only: "This interval is only coverable with emergency fatigue relaxation.",
        generation_hard_constraints: "Hard constraints",
        generation_soft_constraints: "Soft constraints",
        generation_unfilled_count: "Unfilled requirements",
        generation_hard_short: "Hard",
        generation_soft_short: "Soft",
        generation_unfilled_short: "Gap",

        msg_failed_refresh_schedule_data: "Failed to refresh schedule data.",
        msg_server_error_refresh_schedule_data: "Server error while refreshing schedule data.",

        employees_page_title: "Employees",
        employees_page_subtitle: "Create, edit, and manage employee data used for scheduling.",

        employees_form_title: "Employee form",
        employees_form_subtitle: "Fill in the employee data and save it to the system.",

        employees_full_name: "Full name",
        employees_full_name_placeholder: "Enter full name",

        employees_sex: "Sex",
        employees_select_sex: "Select sex",
        employees_sex_male: "Male",
        employees_sex_female: "Female",

        employees_min_shifts: "Min shifts / week",
        employees_target_shifts: "Target shifts / week",
        employees_max_shifts: "Max shifts / week",
        employees_shift_limits_hint: "Make sure minimum, target, and maximum values are logically consistent.",

        employees_rules_title: "Availability rules",
        employees_can_work_night: "Can work night shifts",
        employees_can_work_weekends: "Can work weekends",
        employees_can_work_evenings_after_night: "Can work evening after night",
        employees_can_work_mornings_and_evenings: "Can work morning and evening on the same day",

        employees_add_button: "Add employee",
        employees_update_button: "Update employee",

        employees_list_title: "Employee list",
        employees_list_subtitle: "Current employees available in the system.",

        employees_table_id: "ID",
        employees_table_name: "Full name",
        employees_table_sex: "Sex",
        employees_table_min_target_max: "Min / Target / Max",
        employees_table_night: "Night",
        employees_table_weekends: "Weekends",
        employees_table_evening_after_night: "Evening after night",
        employees_table_morning_evening: "Morning + evening",
        employees_table_actions: "Actions",

        employees_empty_list: "No employees yet",

        employees_edit_button: "Edit",
        employees_delete_button: "Delete",
        msg_failed_load_employees: "Failed to load employees.",
        msg_server_error_load_employees: "Server error while loading employees.",
        msg_enter_employee_full_name: "Please enter full name.",
        msg_select_employee_sex: "Please select sex.",
        msg_min_gt_max_shifts: "Min shifts cannot be greater than max shifts.",
        msg_target_lt_min_shifts: "Target shifts cannot be less than min shifts.",
        msg_target_gt_max_shifts: "Target shifts cannot be greater than max shifts.",
        msg_employee_operation_failed: "Operation failed.",
        msg_server_error_save_employee: "Server error while saving employee.",
        msg_editing_employee: "Editing employee",
        msg_confirm_delete_employee: "Are you sure you want to delete this employee?",
        msg_failed_delete_employee: "Failed to delete employee.",
        msg_server_error_delete_employee: "Server error while deleting employee.",
        msg_confirm_delete_position: "Are you sure you want to delete this position?",
        msg_failed_delete_position: "Failed to delete position.",
        msg_server_error_delete_position: "Server error while deleting position.",

        employees_notes_title: "Notes",
        employees_note_1: "These employees are used later by the schedule generation page.",
        employees_note_2: "One employee may later be assigned to multiple positions.",
        employees_note_3: "The table here is administrative; the schedule page is the main weekly workspace.",

        settings_help_label: "Need help?",
        settings_docs_link: "Documentation",
        settings_guide_link: "User guide",
        settings_backup_title: "Database safety",
        settings_backup_text: "Create manual backups and restore a recent backup if a destructive action needs to be rolled back.",
        settings_backup_create: "Create backup",
        settings_backup_upload_label: "Upload and restore",
        settings_backup_name: "Backup",
        settings_backup_modified: "Modified",
        settings_backup_size: "Size",
        settings_backup_actions: "Actions",
        settings_backup_empty: "No backups yet",
        settings_backup_restore: "Restore",
        settings_backup_created: "Backup created",
        settings_backup_restored: "Backup restored",
        settings_backup_pre_restore: "Current database was preserved as",
        settings_backup_load_failed: "Failed to load backups.",
        settings_backup_create_failed: "Failed to create backup.",
        settings_backup_restore_failed: "Failed to restore backup.",
        settings_backup_restore_confirm: "Restore this backup and replace the current database?",
        settings_backup_empty_title: "No backups yet",
        settings_backup_empty_text: "Create a manual backup before larger cleanup or destructive changes.",
        employees_empty_state_title: "No employees yet",
        employees_empty_state_text: "Add the first employee to unlock assignments, weekly preferences, and scheduling.",
        positions_empty_state_title: "No positions yet",
        positions_empty_state_text: "Add the first position before assigning employees or setting coverage.",
        templates_empty_state_title: "No shift templates yet",
        templates_empty_state_text: "Create reusable shift templates before generating or editing schedules.",
        assignments_empty_state_title: "No assignments yet",
        assignments_empty_state_text: "Link employees to positions so they can appear in the schedule.",
        assignments_missing_prereq_title: "Assignments need employees and positions",
        assignments_missing_prereq_text: "Create employees and positions first, then return here to link them.",
        coverage_empty_state_title: "No coverage requirements yet",
        coverage_empty_state_text: "Add time-based staffing requirements after positions are ready.",
        coverage_missing_positions_title: "Coverage requirements need positions",
        coverage_missing_positions_text: "Create at least one position before adding staffing requirements.",
        preferences_empty_initial_title: "No week loaded",
        preferences_empty_initial_text: "Select a week and an employee to review or update weekly preferences.",
        preferences_empty_no_employees_title: "No employees available",
        preferences_empty_no_employees_text: "Add employees before collecting weekly preferences.",
        common_open_employees: "Open employees",
        common_open_positions: "Open positions",
        common_open_assignments: "Open assignments",

        common_yes: "Yes",
        common_no: "No",
        schedule_workspace_ready_title: "Schedule workspace",
        schedule_workspace_ready_text: "Choose a week and position, then load the table to start editing or generating.",
        schedule_no_positions_title: "Schedule needs positions",
        schedule_no_positions_text: "Create at least one position before loading or generating a weekly schedule.",
        schedule_no_employees_title: "This position has no assigned employees",
        schedule_no_employees_text: "Add employees and link them to this position before filling the week.",
        schedule_action_load_hint: "Load the selected week and position first.",
        schedule_action_generation_hint: "Generation is available after the selected week is loaded.",
        schedule_action_export_hint: "Export becomes available after the selected week is loaded.",
        schedule_action_clear_hint: "Clear week becomes available after the selected week is loaded.",
        preferences_page_title: "Weekly preferences",
        preferences_page_subtitle: "Set weekly employee preferences, restrictions, and preferred day rules.",

        preferences_week_start: "Week start",
        preferences_employee: "Employee",
        preferences_select_employee: "Select employee",

        preferences_load_btn: "Load",
        preferences_save_btn: "Save",

        preferences_initial_hint: "Select a week and an employee, then click Load.",

        preferences_day_column: "Day",
        preferences_date_column: "Date",
        preferences_value_column: "Preference",

        preferences_employee_not_found: "Employee not found",

        preferences_notes_title: "Notes",
        preferences_note_1: "Preferences are stored per employee and per date.",
        preferences_note_2: "These values affect schedule generation and manual validation.",
        preferences_note_3: "The week in this project starts on Sunday.",

        preference_no_preference: "No preference",
        preference_off_day: "Off day",
        preference_only_morning: "Only morning",
        preference_vacation: "Vacation",
        preference_only_evening: "Only evening",
        preference_only_night: "Only night",
        preference_not_morning: "Not morning",
        preference_not_evening: "Not evening",
        preference_not_night: "Not night",
        preference_no_morning_evening_combo: "No morning + evening combo",

        msg_select_employee: "Please select an employee.",
        msg_failed_load_preferences: "Failed to load preferences.",
        msg_server_error_load_preferences: "Server error while loading preferences.",
        msg_preferences_loaded: "Preferences loaded successfully.",
        msg_nothing_to_save: "Nothing to save.",
        msg_some_preferences_not_saved: "Some preferences were not saved.",
        msg_preferences_saved: "Preferences saved successfully.",
        msg_server_error_save_preferences: "Server error while saving preferences.",
        positions_page_title: "Positions",
        positions_page_subtitle: "Create and manage department positions used by the scheduling system.",

        positions_form_title: "Position form",
        positions_form_subtitle: "Add a new position and define coverage-related properties.",

        positions_name: "Position name",
        positions_name_placeholder: "Example: Nurse",

        positions_coverage_title: "Coverage settings",
        positions_requires_continuous_coverage: "Requires continuous coverage",
        positions_minimum_staff_presence: "Minimum staff present at any moment",
        positions_minimum_staff_presence_hint: "Set this only if continuous coverage is required.",

        positions_add_button: "Add position",

        positions_list_title: "Position list",
        positions_list_subtitle: "All positions currently saved in the system.",
        positions_reload_button: "Reload",

        positions_table_id: "ID",
        positions_table_name: "Name",
        positions_table_continuous: "Continuous coverage",
        positions_table_min_presence: "Minimum presence",

        positions_empty_list: "No positions yet",

        positions_notes_title: "Notes",
        positions_note_1: "A position can later be assigned to multiple employees.",
        positions_note_2: "Continuous coverage is useful for roles that require constant presence.",
        positions_note_3: "Minimum staff presence should normally stay at 0 unless continuous coverage is enabled.",

        msg_enter_position_name: "Please enter position name.",
        msg_failed_add_position: "Failed to add position.",
        msg_server_error_save_position: "Server error while saving position.",
        templates_page_title: "Shift templates",
        templates_page_subtitle: "Create and manage reusable shift templates for schedule generation and manual assignment.",

        templates_form_title: "Shift template form",
        templates_form_subtitle: "Add or edit a shift template that belongs to one position.",

        templates_name: "Template name",
        templates_name_placeholder: "Example: Morning 06:30-13:30",
        templates_category: "Shift category",
        templates_select_category: "Select category",

        templates_start_time: "Start time",
        templates_end_time: "End time",

        templates_flags_title: "Template options",
        templates_is_overnight: "Overnight shift",
        templates_is_active: "Active template",
        templates_is_split_only: "Split-shift only",

        templates_add_button: "Add shift template",
        templates_update_button: "Update shift template",

        templates_list_title: "Template list",
        templates_list_subtitle: "All shift templates currently saved in the system, grouped by position.",
        templates_reload_button: "Reload",

        templates_table_id: "ID",
        templates_table_name: "Name",
        templates_table_category: "Category",
        templates_table_start: "Start",
        templates_table_end: "End",
        templates_table_overnight: "Overnight",
        templates_table_active: "Active",
        templates_table_split_only: "Split only",
        templates_table_actions: "Actions",

        templates_empty_list: "No shift templates yet",

        templates_edit_button: "Edit",
        templates_delete_button: "Delete",

        templates_notes_title: "Notes",
        templates_note_1: "Category defines the logical role of the shift: morning, evening, or night.",
        templates_note_2: "Overnight means the shift ends on the following day.",
        templates_note_3: "Split-only templates are intended for paired split shifts, not standalone usage.",

        footer_docs: "Документация",
        footer_guide: "Руководство",
        footer_version: "Schedule App v0.13.3_beta",

        msg_enter_template_name: "Please enter template name.",
        msg_select_shift_category: "Please select shift category.",
        msg_enter_start_end_time: "Please enter start and end time.",
        msg_failed_save_template: "Failed to save shift template.",
        msg_server_error_save_template: "Server error while saving shift template.",

        msg_editing_template: "Editing template",
        msg_confirm_delete_template: "Are you sure you want to delete this shift template?",
        msg_failed_delete_template: "Failed to delete shift template.",
        msg_server_error_delete_template: "Server error while deleting shift template.",

        msg_failed_load_templates: "Failed to load shift templates.",
        msg_server_error_load_templates: "Server error while loading shift templates.",
        assignments_page_title: "Assignments",
        assignments_page_subtitle: "Assign employees to positions and manage their scheduling priority.",

        assignments_form_title: "Assignment form",
        assignments_form_subtitle: "Link one employee to one position and set priority settings.",

        assignments_employee: "Employee",
        assignments_position: "Position",
        assignments_select_employee: "Select employee",
        assignments_select_position: "Select position",

        assignments_priority_score: "Priority score",
        assignments_priority_hint: "Higher values can be used to favor this employee for this position.",

        assignments_options_title: "Assignment options",
        assignments_is_primary: "Primary position for this employee",
        assignments_is_fallback_only: "Fallback only",

        assignments_add_button: "Assign position",

        assignments_list_title: "Assignment list",
        assignments_list_subtitle: "All employee-to-position links currently saved in the system.",
        assignments_reload_button: "Reload",

        assignments_table_employee: "Employee",
        assignments_table_position: "Position",
        assignments_table_primary: "Primary",
        assignments_table_priority: "Priority",
        assignments_table_fallback: "Fallback only",
        assignments_table_actions: "Actions",

        assignments_empty_list: "No assignments yet",
        assignments_delete_button: "Remove",

        assignments_notes_title: "Notes",
        assignments_note_1: "One employee can be assigned to multiple positions.",
        assignments_note_2: "The schedule page uses these assignments to decide who can work in each position.",
        assignments_note_3: "Removing an assignment also removes related schedule entries for that employee and position.",

        msg_failed_load_assignment_data: "Failed to load assignment data.",
        msg_server_error_load_assignment_data: "Server error while loading assignment data.",
        msg_failed_assign_position: "Failed to assign position.",
        msg_server_error_save_assignment: "Server error while saving assignment.",
        msg_confirm_delete_assignment: "Are you sure you want to remove this assignment?",
        msg_failed_delete_assignment: "Failed to delete assignment.",
        msg_server_error_delete_assignment: "Server error while deleting assignment.",
        settings_page_title: "Settings",
        settings_page_subtitle: "Open and manage the administrative sections of the scheduling system.",

        settings_positions_title: "Positions",
        settings_positions_text: "Create and manage department positions used by the scheduling system.",

        settings_templates_title: "Shift templates",
        settings_templates_text: "Create reusable shift templates for each position.",

        settings_assignments_title: "Assignments",
        settings_assignments_text: "Assign employees to positions and define priority or fallback usage.",
        settings_coverage_title: "Coverage requirements",
        settings_coverage_text: "Define how many employees are needed for each time interval.",
        settings_generation_title: "Generation rules",
        settings_generation_text: "Configure emergency limits and cross-position shift behavior for auto-generation.",
        settings_allow_multiple_positions_per_day: "Allow multiple positions in one day",
        settings_max_work_days: "Max work days per week",
        settings_max_nights: "Max consecutive nights",
        settings_emergency_nights: "Emergency night limit",
        settings_max_splits: "Max consecutive split days",
        settings_emergency_splits: "Emergency split limit",
        settings_night_evening_penalty: "Night to evening penalty",
        settings_shortage_weight: "Coverage shortage weight",
        settings_gender_bonus_weight: "Gender target bonus",
        settings_missing_min_weight: "Missing minimum shift weight",
        settings_target_distance_weight: "Target distance weight",
        settings_night_weight: "Night balance weight",
        settings_split_weight: "Split balance weight",
        settings_save_generation: "Save generation settings",
        settings_msg_failed_load_generation: "Failed to load generation settings.",
        settings_msg_failed_save_generation: "Failed to save generation settings.",
        settings_msg_generation_saved: "Generation settings saved.",
        settings_appearance_title: "Appearance",
        settings_appearance_text: "Customize the schedule colors so shift cards are easier to recognize for your team.",
        settings_appearance_preview: "Preview",
        settings_color_morning: "Morning cards",
        settings_color_morning_text: "Used for morning shift cards and legend.",
        settings_color_evening: "Evening cards",
        settings_color_evening_text: "Used for evening shift cards and legend.",
        settings_color_night: "Night cards",
        settings_color_night_text: "Used for night shift cards and legend.",
        settings_color_status: "Status cards",
        settings_color_status_text: "Used for day-off and special status cards.",
        settings_save_appearance: "Save appearance",
        settings_msg_failed_save_appearance: "Failed to save appearance settings.",
        settings_msg_appearance_saved: "Appearance settings saved.",

        settings_notes_title: "Notes",
        settings_note_1: "These sections are administrative and are usually configured less often than the weekly schedule.",
        settings_note_2: "The main weekly workflow still starts from the schedule page.",
        settings_note_3: "If needed later, this page can also include shift requirements and export settings.",

        guide_page_title: "User Guide",
        guide_page_subtitle: "A simple explanation of how to prepare employees, collect preferences, create a schedule, and export it.",
        guide_start_title: "What this app is for",
        guide_start_text: "Schedule App helps you build a weekly work schedule. You enter employees, roles, shift times, staffing needs, and personal preferences. Then you can create the schedule automatically or adjust it by hand.",
        guide_setup_title: "Before creating a schedule",
        guide_setup_text: "Fill in the basic information once, then update it only when something changes.",
        guide_setup_step_1: "Open Employees and add every person who can appear in the schedule.",
        guide_setup_step_2: "Open Settings, then Positions, and create the job roles used in your department.",
        guide_setup_step_3: "Open Shift templates and add the real shift times, such as morning, evening, night, or split shifts.",
        guide_setup_step_4: "Open Assignments and connect each employee to the roles they can work.",
        guide_setup_step_5: "Open Coverage requirements and write how many people are needed during each time period.",
        guide_open_employees: "Open employees",
        guide_open_settings: "Open settings",
        guide_requests_title: "Collect weekly preferences",
        guide_requests_text: "Before planning the week, open Preferences and mark days off, vacations, preferred shifts, and restrictions. This helps the system avoid assigning people when they are unavailable.",
        guide_open_requests: "Open preferences",
        guide_schedule_title: "Create the weekly schedule",
        guide_schedule_text: "Open Schedule, choose the week and position, then load the table. Use Auto generate to let the system fill shifts. Review the warnings, then make any manual changes you need.",
        guide_schedule_step_1: "Choose the first day of the week.",
        guide_schedule_step_2: "Choose the position you want to schedule.",
        guide_schedule_step_3: "Click Load to see the current schedule.",
        guide_schedule_step_4: "Click Auto generate if you want the app to fill missing shifts.",
        guide_schedule_step_5: "Check warnings and coverage rows before you finish.",
        guide_open_schedule: "Open schedule",
        guide_manual_title: "Manual changes",
        guide_manual_text: "You can add or delete shifts manually. You can also mark a person as sick, day off, or no-show. Use these options when the real situation changes after the schedule was created.",
        guide_export_title: "Share the schedule",
        guide_export_text: "When the week looks correct, use Export Excel on the Schedule page. The file is meant for printing, sending, or keeping as a weekly record.",
        guide_help_title: "If something looks wrong",
        guide_help_step_1: "Check that the employee is assigned to the selected position.",
        guide_help_step_2: "Check that the employee is not blocked by a day off, vacation, sickness, or request.",
        guide_help_step_3: "Check that the shift template is active and has the correct time.",
        guide_help_step_4: "Check Coverage requirements to make sure the needed number of people is correct.",
        guide_contents_title: "On this page",
        guide_contents_text: "Use these links to jump to the part you need.",
        guide_contents_start: "Purpose",
        guide_contents_setup: "Setup",
        guide_contents_requests: "Preferences",
        guide_contents_schedule: "Schedule",
        guide_contents_manual: "Manual changes",
        guide_contents_export: "Export",
        guide_contents_help: "Help",

        common_actions: "Actions",
        common_back: "Back",
        common_reload: "Reload",
        common_reset: "Reset",
        common_edit: "Edit",
        common_delete: "Delete",
        common_cancel: "Cancel",
        common_confirm: "Confirm",
        common_recovery_backup: "Recovery backup",

        coverage_page_title: "Coverage requirements",
        coverage_page_subtitle: "Time-based staffing requirements by position.",
        coverage_rest_title: "Rest settings",
        coverage_rest_subtitle: "Configure minimum rest gaps used by manual validation and auto-generation.",
        coverage_rest_morning_evening: "Morning to evening rest, minutes",
        coverage_rest_night_evening: "Night to evening rest, minutes",
        coverage_save_rest_settings: "Save rest settings",
        coverage_display_mode: "Schedule coverage display",
        coverage_display_interval: "By time intervals",
        coverage_display_category: "By shift categories",
        coverage_start_time: "Start",
        coverage_end_time: "End",
        coverage_staff_required: "Staff",
        coverage_women_required: "Women",
        coverage_men_required: "Men",
        coverage_overnight: "Overnight",
        coverage_add_button: "Add",
        coverage_update_button: "Update",
        coverage_table_id: "ID",
        coverage_table_time: "Time",
        coverage_empty_list: "No coverage requirements yet",
        coverage_msg_failed_load_rest: "Failed to load rest settings.",
        coverage_msg_failed_save_rest: "Failed to save rest settings.",
        coverage_msg_women_gt_staff: "Women minimum cannot be greater than staff total.",
        coverage_msg_men_gt_staff: "Men minimum cannot be greater than staff total.",
        coverage_msg_gender_gt_staff: "Women and men minimums cannot be greater than staff total.",
        coverage_msg_failed_save: "Failed to save coverage requirement.",
        coverage_msg_failed_load: "Failed to load coverage requirements.",
        coverage_msg_confirm_delete: "Delete coverage requirement?",
        coverage_msg_failed_delete: "Failed to delete coverage requirement."
    },

    ru: {
        app_title: "Schedule App",
        app_subtitle: "Составление расписания персонала",

        nav_section_main: "Основное",
        nav_dashboard: "Главная",
        nav_schedule: "Расписание",
        nav_employees: "Сотрудники",
        nav_requests: "Пожелания",
        nav_settings: "Настройки",

        sidebar_footer_title: "Версия 0.13.3_beta",
        sidebar_footer_text: "Сейчас идёт редизайн интерфейса. Главная цель — сделать рабочий процесс проще и понятнее.",

        page_title: "Главная",
        page_subtitle: "Более чистый и понятный центр управления недельным расписанием.",

        home_title: "Главное меню",
        home_subtitle: "Выберите действие, которое нужно вам сейчас.",

        home_schedule_title: "Составить расписание",
        home_schedule_text: "Открыть недельное расписание и создать или изменить смены.",

        home_employees_title: "Сотрудники",
        home_employees_text: "Добавление, редактирование и управление сотрудниками.",

        home_requests_title: "Пожелания",
        home_requests_text: "Просмотр недельных пожеланий, выходных и запросов.",

        home_settings_title: "Настройки",
        home_settings_text: "Настройка должностей, шаблонов смен и системных данных.",

        toggle_sidebar: "Свернуть или развернуть меню",

        lang_he: "עברית",
        lang_en: "English",
        lang_ru: "Русский",

        hero_title: "Недельное расписание без визуального хаоса",
        hero_text: "Эта версия делает упор на ясность, скорость и более минималистичный рабочий интерфейс для повседневного использования.",
        hero_open_schedule: "Открыть расписание",
        hero_manage_employees: "Сотрудники",
        hero_system_settings: "Настройки системы",

        stats_title: "Эта неделя",
        stat_morning: "Покрытие утра",
        stat_evening: "Покрытие вечера",
        stat_night: "Покрытие ночи",
        stat_morning_value: "93%",
        stat_evening_value: "88%",
        stat_night_value: "100%",
        stat_morning_note: "Почти заполнено",
        stat_evening_note: "Нужно внимание",
        stat_night_note: "Полностью закрыто",

        footer_docs: "Документация",
        footer_guide: "Руководство",
        footer_version: "Schedule App v0.13.3_beta",

        quick_actions_title: "Быстрые действия",
        quick_action_schedule_title: "Открыть текущую неделю",
        quick_action_schedule_text: "Перейти прямо к недельному расписанию и продолжить редактирование.",
        quick_action_generate_title: "Автогенерация",
        quick_action_generate_text: "Запустить алгоритм и быстрее заполнить оставшиеся смены.",
        quick_action_export_title: "Экспорт Excel",
        quick_action_export_text: "Подготовить недельный график для печати и передачи.",
        quick_action_requests_title: "Пожелания сотрудников",
        quick_action_requests_text: "Просмотреть предпочтения, выходные, отпуска и ограничения.",

        alerts_title: "Предупреждения и заметки",
        alert_1_title: "Утро вторника",
        alert_1_text: "Для полного покрытия всё ещё нужен ещё один сотрудник.",
        alert_2_title: "Вечер среды",
        alert_2_text: "Минимальное требование по количеству женщин пока не выполнено.",
        alert_3_title: "Ночь пятницы",
        alert_3_text: "Ночная смена закрыта полностью и не требует изменений.",

        settings_help_label: "Нужна помощь?",
        settings_docs_link: "Документация",
        settings_guide_link: "Руководство",
        settings_backup_title: "Безопасность базы данных",
        settings_backup_text: "Создавайте ручные резервные копии и восстанавливайте недавнюю копию, если нужно откатить опасное изменение.",
        settings_backup_create: "Создать копию",
        settings_backup_upload_label: "Загрузить и восстановить",
        settings_backup_name: "Копия",
        settings_backup_modified: "Изменён",
        settings_backup_size: "Размер",
        settings_backup_actions: "Действия",
        settings_backup_empty: "Резервных копий пока нет",
        settings_backup_restore: "Восстановить",
        settings_backup_created: "Резервная копия создана",
        settings_backup_restored: "Резервная копия восстановлена",
        settings_backup_pre_restore: "Текущая база была сохранена как",
        settings_backup_load_failed: "Не удалось загрузить резервные копии.",
        settings_backup_create_failed: "Не удалось создать резервную копию.",
        settings_backup_restore_failed: "Не удалось восстановить резервную копию.",
        settings_backup_restore_confirm: "Восстановить эту резервную копию и заменить текущую базу данных?",
        settings_backup_empty_title: "Резервных копий пока нет",
        settings_backup_empty_text: "Создайте ручную резервную копию перед крупной чисткой или удалениями.",
        employees_empty_state_title: "Сотрудников пока нет",
        employees_empty_state_text: "Добавьте первого сотрудника, чтобы открыть назначения, недельные пожелания и составление расписания.",
        positions_empty_state_title: "Должностей пока нет",
        positions_empty_state_text: "Добавьте первую должность перед назначением сотрудников и настройкой покрытия.",
        templates_empty_state_title: "Шаблонов смен пока нет",
        templates_empty_state_text: "Создайте шаблоны смен до автогенерации или ручного редактирования расписания.",
        assignments_empty_state_title: "Назначений пока нет",
        assignments_empty_state_text: "Свяжите сотрудников с должностями, чтобы они могли появляться в расписании.",
        assignments_missing_prereq_title: "Для назначений нужны сотрудники и должности",
        assignments_missing_prereq_text: "Сначала создайте сотрудников и должности, затем вернитесь сюда для связки.",
        coverage_empty_state_title: "Требований покрытия пока нет",
        coverage_empty_state_text: "Добавьте требования по времени после настройки должностей.",
        coverage_missing_positions_title: "Для требований покрытия нужны должности",
        coverage_missing_positions_text: "Создайте хотя бы одну должность перед добавлением требований по персоналу.",
        preferences_empty_initial_title: "Неделя не загружена",
        preferences_empty_initial_text: "Выберите неделю и сотрудника, чтобы просмотреть или обновить недельные пожелания.",
        preferences_empty_no_employees_title: "Нет доступных сотрудников",
        preferences_empty_no_employees_text: "Добавьте сотрудников перед сбором недельных пожеланий.",
        common_open_employees: "Открыть сотрудников",
        common_open_positions: "Открыть должности",
        common_open_assignments: "Открыть назначения",

        summary_title: "Текущее рабочее пространство",
        summary_week: "Выбранная неделя",
        summary_position: "Выбранная должность",
        summary_language: "Язык интерфейса",
        summary_status: "Статус редизайна",
        summary_status_value: "База готова",

        summary_badge: "Поддерживается RTL для иврита",
        schedule_workspace_ready_title: "Рабочая область расписания",
        schedule_workspace_ready_text: "Выберите неделю и должность, затем загрузите таблицу для редактирования или генерации.",
        schedule_no_positions_title: "Для расписания нужны должности",
        schedule_no_positions_text: "Создайте хотя бы одну должность перед загрузкой или генерацией недельного расписания.",
        schedule_no_employees_title: "У этой должности нет назначенных сотрудников",
        schedule_no_employees_text: "Добавьте сотрудников и свяжите их с этой должностью перед заполнением недели.",
        schedule_action_load_hint: "Сначала загрузите выбранную неделю и должность.",
        schedule_action_generation_hint: "Генерация доступна после загрузки выбранной недели.",
        schedule_action_export_hint: "Экспорт станет доступен после загрузки выбранной недели.",
        schedule_action_clear_hint: "Очистка недели доступна после загрузки выбранной недели.",
        schedule_page_title: "Расписание",
        schedule_page_subtitle: "Управляйте недельным расписанием, запускайте генерацию и экспортируйте результат.",

        schedule_week_start: "Начало недели",
        schedule_position: "Должность",
        schedule_select_position: "Выберите должность",

        schedule_load_btn: "Загрузить",
        schedule_generate_btn: "Автогенерация",
        schedule_generate_all_btn: "Сгенерировать всё",
        schedule_generating_title: "Составляем расписание",
        schedule_generating_text: "Алгоритм проверяет покрытие, правила отдыха и лимиты сотрудников.",
        schedule_clear_btn: "Очистить неделю",
        schedule_export_btn: "Экспорт Excel",
        schedule_clear_message_btn: "Очистить сообщение",
        schedule_toolbar_generate: "Генерация",
        schedule_toolbar_output: "Вывод",
        schedule_toolbar_danger: "Опасные действия",
        schedule_status_legend: "Статус",
        schedule_status_week: "Неделя",
        schedule_status_position: "Должность",
        schedule_status_staff: "Сотрудники",
        schedule_status_shifts: "Смены",
        schedule_status_gaps: "пробелов",

        schedule_initial_hint: "Выберите неделю и должность, затем загрузите расписание.",

        schedule_add_shift: "Добавить смену",
        schedule_select_shift_template: "Выберите шаблон смены",
        schedule_add_shift_btn: "Добавить смену",

        schedule_day_status: "Статус дня",
        schedule_no_status: "Без статуса",
        schedule_save_status_btn: "Сохранить статус",

        schedule_manual_day_status: "Статус дня вручную",
        schedule_no_shifts_assigned: "Смены не назначены",
        schedule_other_positions_label: "Другие должности",
        schedule_delete_shift_btn: "Удалить",

        schedule_employee_header: "Сотрудник",
        schedule_coverage_header: "Покрытие",
        schedule_no_employees_for_position: "К этой должности не привязан ни один сотрудник.",

        employee_min_target_max: "Мин/Цель/Макс",

        shift_morning: "Утро",
        shift_evening: "Вечер",
        shift_night: "Ночь",

        status_sick: "Больничный",
        status_day_off: "Выходной",
        status_no_show: "Неявка",
        schedule_remove_status: "Удалить статус",
        schedule_shift_status: "Статус смены",
        schedule_status_sick_hint: "Закрывает всю ячейку дня",
        schedule_status_day_off_hint: "Отмечает весь день как выходной",
        schedule_no_shifts_for_no_show: "Нет смен, доступных для статуса неявки",

        coverage_staff: "Сотрудники",
        coverage_women: "Женщины",
        coverage_men: "Мужчины",
        coverage_intervals_short: "слотов",

        weekday_sunday: "Воскресенье",
        weekday_monday: "Понедельник",
        weekday_tuesday: "Вторник",
        weekday_wednesday: "Среда",
        weekday_thursday: "Четверг",
        weekday_friday: "Пятница",
        weekday_saturday: "Суббота",

        msg_failed_load_positions: "Не удалось загрузить должности.",
        msg_server_error_load_positions: "Ошибка сервера при загрузке должностей.",

        msg_select_week_start: "Пожалуйста, выберите дату начала недели.",
        msg_select_position: "Пожалуйста, выберите должность.",

        msg_failed_load_schedule_data: "Не удалось загрузить данные расписания.",
        msg_server_error_load_schedule: "Ошибка сервера при загрузке расписания.",
        msg_schedule_loaded: "Расписание успешно загружено.",
        msg_failed_save_schedule_display: "Не удалось сохранить режим отображения покрытия.",

        msg_auto_generate_failed: "Автогенерация не удалась.",
        msg_auto_generate_done: "Автогенерация завершена.",
        schedule_generate_all_done: "Автогенерация по всем должностям завершена.",
        schedule_generate_all_success_summary: "Сгенерировано должностей",
        schedule_generate_all_created_summary: "Создано смен",
        schedule_generate_all_failures_prefix: "Ошибки по должностям",
        msg_created_count: "Создано",
        msg_optimization_moved: "Оптимизировано перестановок",
        msg_warnings: "Предупреждения",
        msg_server_error_auto_generate: "Ошибка сервера при автогенерации расписания.",
        generation_summary_title: "Сводка генерации",
        generation_summary_subtitle: "Последний результат автогенерации для выбранной недели и должности.",
        generation_summary_clear_btn: "Очистить сводку",
        generation_summary_open_panel: "Подробный результат генерации показан в панели сводки.",
        generation_created_note: "Новые записи расписания, добавленные автогенерацией.",
        generation_optimized_note: "Уже созданные записи были перераспределены для лучшего баланса.",
        generation_day_off_count: "Сгенерировано выходных",
        generation_day_off_note: "Автоматически созданные статусы выходного для незаполненных дней сотрудников.",
        generation_hard_note: "Блокирующие проблемы, найденные на предварительной проверке.",
        generation_soft_note: "Предупреждения, которые не остановили генерацию.",
        generation_unfilled_note: "Пробелы в покрытии, которые остались после генерации.",
        generation_run_overview: "Обзор прогона",
        generation_summary_week: "Неделя",
        generation_summary_position: "Должность",
        generation_summary_status: "Статус выполнимости",
        generation_feasibility_status_ok: "ОК",
        generation_feasibility_status_blocking: "Блокирующий",
        generation_unfilled_title: "Оставшиеся незакрытые требования",
        generation_summary_clean_title: "Чистый результат генерации",
        generation_summary_clean_text: "Генерация завершилась без предупреждений, жёстких блокеров и оставшихся незакрытых требований.",
        generation_missing_total: "Не хватает всего",
        generation_missing_female: "Не хватает женщин",
        generation_missing_male: "Не хватает мужчин",
        generation_reasons: "Причины",

        msg_confirm_clear_week: "Вы уверены, что хотите удалить расписание за эту неделю для этой должности?",
        msg_confirm_clear_week_title: "Очистка расписания недели",
        msg_failed_clear_week: "Не удалось очистить расписание за неделю.",
        msg_week_cleared: "Расписание за неделю очищено.",
        msg_deleted_count: "Удалено",
        confirm_impact_position: "Должность",
        confirm_impact_employee: "Сотрудник",
        confirm_impact_template: "Шаблон",
        confirm_impact_assignment: "Назначение",
        confirm_impact_week: "Неделя",
        confirm_impact_schedule_entries: "Записи расписания",
        confirm_impact_assignments: "Назначения",
        confirm_impact_general_preferences: "Общие пожелания",
        confirm_impact_weekly_preferences: "Недельные пожелания",
        confirm_impact_day_statuses: "Статусы дней",
        confirm_impact_day_off_statuses: "Статусы выходного",
        confirm_impact_shift_requirements: "Требования по сменам",
        confirm_impact_coverage_requirements: "Требования покрытия",
        confirm_impact_assigned_employees: "Назначенные сотрудники",
        confirm_impact_in_use_warning: "Этот шаблон уже используется в расписании, и удаление будет заблокировано.",
        confirm_impact_fetch_failed: "Не удалось загрузить связанные записи. Проверьте последствия перед удалением.",
        msg_server_error_clear_week: "Ошибка сервера при очистке недели.",

        msg_select_shift_template_first: "Сначала выберите шаблон смены.",
        msg_status_selector_not_found: "Селектор статуса не найден.",

        msg_failed_add_shift: "Не удалось добавить смену.",
        msg_shift_added: "Смена успешно добавлена.",
        msg_server_error_add_shift: "Ошибка сервера при добавлении смены.",

        msg_failed_delete_shift: "Не удалось удалить смену.",
        msg_shift_deleted: "Смена успешно удалена.",
        msg_server_error_delete_shift: "Ошибка сервера при удалении смены.",

        msg_failed_save_day_status: "Не удалось сохранить статус дня.",
        msg_day_status_saved: "Статус дня успешно сохранён.",
        msg_server_error_save_day_status: "Ошибка сервера при сохранении статуса дня.",
        msg_failed_save_shift_status: "Не удалось сохранить статус смены.",
        msg_no_show_saved: "Статус неявки сохранён.",
        msg_no_show_removed: "Статус неявки удалён.",
        msg_server_error_save_shift_status: "Ошибка сервера при сохранении статуса смены.",

        generation_warning_no_active_slots_week: "Нет активных интервалов покрытия на эту неделю",
        generation_warning_no_active_slots_day: "Нет активных интервалов покрытия на этот день",
        generation_warning_emergency_fatigue: "использовано аварийное ослабление правил усталости для закрытия интервала",
        generation_warning_underfilled: "не закрыто полностью",
        generation_warning_reasons: "Причины:",
        generation_warning_worked_days: "имеет рабочие дни без обязательного недельного выходного",
        generation_warning_consecutive_nights: "ночных смен подряд",
        generation_warning_consecutive_splits: "сплит-смен подряд",
        generation_reason_not_enough_female: "недостаточно доступных сотрудниц",
        generation_reason_not_enough_male: "недостаточно доступных сотрудников-мужчин",
        generation_reason_split_pair: "для сплит-шаблона нет допустимой пары",
        generation_reason_day_status: "статус дня блокирует сотрудника",
        generation_reason_not_assigned: "сотрудник не привязан к этой должности",
        generation_reason_max_shifts: "сотрудник достиг максимума смен",
        generation_reason_weekly_max_shifts: "сотрудник достиг недельного максимума смен",
        generation_reason_preference_or_permission: "пожелания или ограничения сотрудника блокируют эту смену",
        generation_reason_mandatory_day_off: "будет нарушен обязательный недельный выходной",
        generation_reason_overlapping_shift: "у сотрудника уже есть пересекающаяся смена",
        generation_reason_cannot_split_day: "сотрудник не может работать утро и вечер в один день",
        generation_reason_unpairable_shift_type: "у сотрудника уже есть другой тип смены, который нельзя сочетать",
        generation_reason_split_only_combo: "комбинация утро-вечер требует только split-шаблоны",
        generation_reason_weekly_preference_split: "недельное пожелание блокирует комбинацию утро-вечер",
        generation_reason_two_shifts_day: "у сотрудника уже две смены в этот день",
        generation_reason_off_or_vacation: "у сотрудника выходной или отпуск",
        generation_reason_preference_conflict: "смена конфликтует с пожеланием сотрудника",
        generation_reason_morning_after_night: "утро после ночи запрещено",
        generation_reason_night_evening_rest: "недостаточно отдыха после ночи перед вечерней сменой",
        generation_reason_morning_evening_rest: "недостаточно отдыха между утренней и вечерней сменой",
        generation_reason_weekly_day_off: "будет нарушен обязательный недельный выходной",
        generation_reason_consecutive_nights: "достигнут лимит ночных смен подряд",
        generation_reason_consecutive_splits: "достигнут лимит сплит-смен подряд",
        generation_reason_too_many_consecutive_nights: "слишком много ночных смен подряд",
        generation_reason_too_many_consecutive_splits: "слишком много сплит-смен подряд",
        generation_reason_no_coverage_gain: "кандидаты были, но они не улучшали покрытие без переполнения других интервалов",
        generation_precheck_blocking: "Предварительная проверка, блокирующая проблема:",
        generation_precheck_warning: "Предварительная проверка, предупреждение:",
        generation_precheck_no_slots: "Не удалось построить активные интервалы покрытия из требований.",
        generation_precheck_no_template: "Нет активного шаблона смены, который закрывает этот обязательный интервал.",
        generation_precheck_no_legacy_template: "Нет активного не-сплит шаблона для этого требования к смене.",
        generation_precheck_staff_shortage: "Требуется больше сотрудников, чем назначено на эту должность.",
        generation_precheck_female_shortage: "Требуется больше женщин, чем доступно среди сотрудников.",
        generation_precheck_male_shortage: "Требуется больше мужчин, чем доступно среди сотрудников.",
        generation_precheck_no_candidate: "Нет подходящей пары сотрудник/шаблон для закрытия этого интервала.",
        generation_precheck_emergency_only: "Этот интервал закрывается только с аварийным ослаблением правил усталости.",
        generation_hard_constraints: "Жёсткие ограничения",
        generation_soft_constraints: "Мягкие ограничения",
        generation_unfilled_count: "Незакрытые требования",
        generation_hard_short: "Жёстк.",
        generation_soft_short: "Мягк.",
        generation_unfilled_short: "Пробел",

        msg_failed_refresh_schedule_data: "Не удалось обновить данные расписания.",
        msg_server_error_refresh_schedule_data: "Ошибка сервера при обновлении данных расписания.",
        employees_page_title: "Сотрудники",
        employees_page_subtitle: "Создание, редактирование и управление данными сотрудников для составления расписания.",

        employees_form_title: "Форма сотрудника",
        employees_form_subtitle: "Заполните данные сотрудника и сохраните их в системе.",

        employees_full_name: "Полное имя",
        employees_full_name_placeholder: "Введите полное имя",

        employees_sex: "Пол",
        employees_select_sex: "Выберите пол",
        employees_sex_male: "Мужской",
        employees_sex_female: "Женский",

        employees_min_shifts: "Мин. смен / неделя",
        employees_target_shifts: "Целевые смены / неделя",
        employees_max_shifts: "Макс. смен / неделя",
        employees_shift_limits_hint: "Убедитесь, что минимальное, целевое и максимальное значения логически согласованы.",

        employees_rules_title: "Правила доступности",
        employees_can_work_night: "Может работать в ночные смены",
        employees_can_work_weekends: "Может работать по выходным",
        employees_can_work_evenings_after_night: "Может работать вечером после ночной смены",
        employees_can_work_mornings_and_evenings: "Может работать утром и вечером в один день",

        employees_add_button: "Добавить сотрудника",
        employees_update_button: "Обновить сотрудника",

        employees_list_title: "Список сотрудников",
        employees_list_subtitle: "Текущие сотрудники, доступные в системе.",

        employees_table_id: "ID",
        employees_table_name: "Полное имя",
        employees_table_sex: "Пол",
        employees_table_min_target_max: "Мин / Цель / Макс",
        employees_table_night: "Ночь",
        employees_table_weekends: "Выходные",
        employees_table_evening_after_night: "Вечер после ночи",
        employees_table_morning_evening: "Утро + вечер",
        employees_table_actions: "Действия",

        employees_empty_list: "Сотрудников пока нет",

        employees_edit_button: "Редактировать",
        employees_delete_button: "Удалить",
        msg_failed_load_employees: "Не удалось загрузить сотрудников.",
        msg_server_error_load_employees: "Ошибка сервера при загрузке сотрудников.",
        msg_enter_employee_full_name: "Пожалуйста, введите полное имя.",
        msg_select_employee_sex: "Пожалуйста, выберите пол.",
        msg_min_gt_max_shifts: "Минимум смен не может быть больше максимума.",
        msg_target_lt_min_shifts: "Цель смен не может быть меньше минимума.",
        msg_target_gt_max_shifts: "Цель смен не может быть больше максимума.",
        msg_employee_operation_failed: "Операция не выполнена.",
        msg_server_error_save_employee: "Ошибка сервера при сохранении сотрудника.",
        msg_editing_employee: "Редактируется сотрудник",
        msg_confirm_delete_employee: "Вы уверены, что хотите удалить этого сотрудника?",
        msg_failed_delete_employee: "Не удалось удалить сотрудника.",
        msg_server_error_delete_employee: "Ошибка сервера при удалении сотрудника.",
        msg_confirm_delete_position: "Вы уверены, что хотите удалить эту должность?",
        msg_failed_delete_position: "Не удалось удалить должность.",
        msg_server_error_delete_position: "Ошибка сервера при удалении должности.",

        employees_notes_title: "Заметки",
        employees_note_1: "Эти сотрудники позже используются на странице генерации расписания.",
        employees_note_2: "Один сотрудник в дальнейшем может быть привязан к нескольким должностям.",
        employees_note_3: "Эта таблица — административная, а страница расписания остаётся основным рабочим экраном.",

        common_yes: "Да",
        common_no: "Нет",
        preferences_page_title: "Недельные пожелания",
        preferences_page_subtitle: "Задавайте недельные пожелания сотрудников, ограничения и правила по дням.",

        preferences_week_start: "Начало недели",
        preferences_employee: "Сотрудник",
        preferences_select_employee: "Выберите сотрудника",

        preferences_load_btn: "Загрузить",
        preferences_save_btn: "Сохранить",

        preferences_initial_hint: "Выберите неделю и сотрудника, затем нажмите Загрузить.",

        preferences_day_column: "День",
        preferences_date_column: "Дата",
        preferences_value_column: "Пожелание",

        preferences_employee_not_found: "Сотрудник не найден",

        preferences_notes_title: "Заметки",
        preferences_note_1: "Пожелания сохраняются для конкретного сотрудника и конкретной даты.",
        preferences_note_2: "Эти значения влияют на автогенерацию и ручную проверку расписания.",
        preferences_note_3: "В этом проекте неделя начинается с воскресенья.",

        preference_no_preference: "Без пожелания",
        preference_off_day: "Выходной",
        preference_only_morning: "Только утро",
        preference_vacation: "Отпуск",
        preference_only_evening: "Только вечер",
        preference_only_night: "Только ночь",
        preference_not_morning: "Не утро",
        preference_not_evening: "Не вечер",
        preference_not_night: "Не ночь",
        preference_no_morning_evening_combo: "Без комбинации утро + вечер",

        msg_select_employee: "Пожалуйста, выберите сотрудника.",
        msg_failed_load_preferences: "Не удалось загрузить пожелания.",
        msg_server_error_load_preferences: "Ошибка сервера при загрузке пожеланий.",
        msg_preferences_loaded: "Пожелания успешно загружены.",
        msg_nothing_to_save: "Нечего сохранять.",
        msg_some_preferences_not_saved: "Некоторые пожелания не были сохранены.",
        msg_preferences_saved: "Пожелания успешно сохранены.",
        msg_server_error_save_preferences: "Ошибка сервера при сохранении пожеланий.",
        positions_page_title: "Должности",
        positions_page_subtitle: "Создание и управление должностями отдела, используемыми системой расписания.",

        positions_form_title: "Форма должности",
        positions_form_subtitle: "Добавьте новую должность и задайте свойства, связанные с покрытием.",

        positions_name: "Название должности",
        positions_name_placeholder: "Пример: Медсестра",

        positions_coverage_title: "Настройки покрытия",
        positions_requires_continuous_coverage: "Требуется непрерывное покрытие",
        positions_minimum_staff_presence: "Минимум сотрудников в любой момент времени",
        positions_minimum_staff_presence_hint: "Указывайте это только если включено непрерывное покрытие.",

        positions_add_button: "Добавить должность",

        positions_list_title: "Список должностей",
        positions_list_subtitle: "Все должности, сохранённые в системе.",
        positions_reload_button: "Обновить",

        positions_table_id: "ID",
        positions_table_name: "Название",
        positions_table_continuous: "Непрерывное покрытие",
        positions_table_min_presence: "Минимум присутствия",

        positions_empty_list: "Должностей пока нет",

        positions_notes_title: "Заметки",
        positions_note_1: "Одна должность в дальнейшем может быть назначена нескольким сотрудникам.",
        positions_note_2: "Непрерывное покрытие полезно для ролей, где требуется постоянное присутствие.",
        positions_note_3: "Минимум присутствия обычно должен оставаться 0, если непрерывное покрытие не включено.",

        msg_enter_position_name: "Пожалуйста, введите название должности.",
        msg_failed_add_position: "Не удалось добавить должность.",
        msg_server_error_save_position: "Ошибка сервера при сохранении должности.",
        templates_page_title: "Шаблоны смен",
        templates_page_subtitle: "Создание и управление шаблонами смен для автогенерации и ручного назначения.",

        templates_form_title: "Форма шаблона смены",
        templates_form_subtitle: "Добавьте или отредактируйте шаблон смены, привязанный к одной должности.",

        templates_name: "Название шаблона",
        templates_name_placeholder: "Пример: Утро 06:30-13:30",
        templates_category: "Категория смены",
        templates_select_category: "Выберите категорию",

        templates_start_time: "Время начала",
        templates_end_time: "Время окончания",

        templates_flags_title: "Параметры шаблона",
        templates_is_overnight: "Ночная переходящая смена",
        templates_is_active: "Активный шаблон",
        templates_is_split_only: "Только для сплит-смен",

        templates_add_button: "Добавить шаблон смены",
        templates_update_button: "Обновить шаблон смены",

        templates_list_title: "Список шаблонов",
        templates_list_subtitle: "Все шаблоны смен, сохранённые в системе и распределённые по должностям.",
        templates_reload_button: "Обновить",

        templates_table_id: "ID",
        templates_table_name: "Название",
        templates_table_category: "Категория",
        templates_table_start: "Начало",
        templates_table_end: "Конец",
        templates_table_overnight: "Переходящая",
        templates_table_active: "Активна",
        templates_table_split_only: "Только сплит",
        templates_table_actions: "Действия",

        templates_empty_list: "Шаблонов смен пока нет",

        templates_edit_button: "Редактировать",
        templates_delete_button: "Удалить",

        templates_notes_title: "Заметки",
        templates_note_1: "Категория определяет логическую роль смены: утро, вечер или ночь.",
        templates_note_2: "Переходящая смена означает, что она заканчивается на следующий день.",
        templates_note_3: "Шаблоны только для сплит-смен предназначены для парных сплит-смен, а не для одиночного использования.",

        msg_enter_template_name: "Пожалуйста, введите название шаблона.",
        msg_select_shift_category: "Пожалуйста, выберите категорию смены.",
        msg_enter_start_end_time: "Пожалуйста, укажите время начала и окончания.",
        msg_failed_save_template: "Не удалось сохранить шаблон смены.",
        msg_server_error_save_template: "Ошибка сервера при сохранении шаблона смены.",

        msg_editing_template: "Редактируется шаблон",
        msg_confirm_delete_template: "Вы уверены, что хотите удалить этот шаблон смены?",
        msg_failed_delete_template: "Не удалось удалить шаблон смены.",
        msg_server_error_delete_template: "Ошибка сервера при удалении шаблона смены.",

        msg_failed_load_templates: "Не удалось загрузить шаблоны смен.",
        msg_server_error_load_templates: "Ошибка сервера при загрузке шаблонов смен.",
        assignments_page_title: "Назначения",
        assignments_page_subtitle: "Назначайте сотрудников на должности и управляйте их приоритетом в расписании.",

        assignments_form_title: "Форма назначения",
        assignments_form_subtitle: "Свяжите одного сотрудника с одной должностью и задайте настройки приоритета.",

        assignments_employee: "Сотрудник",
        assignments_position: "Должность",
        assignments_select_employee: "Выберите сотрудника",
        assignments_select_position: "Выберите должность",

        assignments_priority_score: "Баллы приоритета",
        assignments_priority_hint: "Более высокие значения можно использовать, чтобы чаще выбирать этого сотрудника для этой должности.",

        assignments_options_title: "Параметры назначения",
        assignments_is_primary: "Основная должность для этого сотрудника",
        assignments_is_fallback_only: "Только как резерв",

        assignments_add_button: "Назначить должность",

        assignments_list_title: "Список назначений",
        assignments_list_subtitle: "Все связи сотрудник-должность, сохранённые в системе.",
        assignments_reload_button: "Обновить",

        assignments_table_employee: "Сотрудник",
        assignments_table_position: "Должность",
        assignments_table_primary: "Основная",
        assignments_table_priority: "Приоритет",
        assignments_table_fallback: "Только резерв",
        assignments_table_actions: "Действия",

        assignments_empty_list: "Назначений пока нет",
        assignments_delete_button: "Удалить",

        assignments_notes_title: "Заметки",
        assignments_note_1: "Один сотрудник может быть назначен на несколько должностей.",
        assignments_note_2: "Страница расписания использует эти связи, чтобы определить, кто может работать на каждой должности.",
        assignments_note_3: "Удаление связи также удаляет связанные записи расписания для этого сотрудника и должности.",

        msg_failed_load_assignment_data: "Не удалось загрузить данные назначений.",
        msg_server_error_load_assignment_data: "Ошибка сервера при загрузке данных назначений.",
        msg_failed_assign_position: "Не удалось назначить должность.",
        msg_server_error_save_assignment: "Ошибка сервера при сохранении назначения.",
        msg_confirm_delete_assignment: "Вы уверены, что хотите удалить это назначение?",
        msg_failed_delete_assignment: "Не удалось удалить назначение.",
        msg_server_error_delete_assignment: "Ошибка сервера при удалении назначения.",
        settings_page_title: "Настройки",
        settings_page_subtitle: "Открывайте и управляйте административными разделами системы расписания.",

        settings_positions_title: "Должности",
        settings_positions_text: "Создание и управление должностями отдела, используемыми системой расписания.",

        settings_templates_title: "Шаблоны смен",
        settings_templates_text: "Создание шаблонов смен отдельно для каждой должности.",

        settings_assignments_title: "Назначения",
        settings_assignments_text: "Связывайте сотрудников с должностями и задавайте приоритет или резервную роль.",

        settings_coverage_title: "Требования покрытия",
        settings_coverage_text: "Задайте, сколько сотрудников нужно на каждом временном интервале.",
        settings_generation_title: "Правила генерации",
        settings_generation_text: "Настройка аварийных лимитов и поведения смен между должностями для автогенерации.",
        settings_allow_multiple_positions_per_day: "Разрешить несколько должностей в один день",
        settings_max_work_days: "Максимум рабочих дней в неделю",
        settings_max_nights: "Максимум ночей подряд",
        settings_emergency_nights: "Аварийный лимит ночей",
        settings_max_splits: "Максимум сплит-дней подряд",
        settings_emergency_splits: "Аварийный лимит сплит-дней",
        settings_night_evening_penalty: "Штраф ночь → вечер",
        settings_shortage_weight: "Вес недобора покрытия",
        settings_gender_bonus_weight: "Бонус целевого пола",
        settings_missing_min_weight: "Вес недобора минимума смен",
        settings_target_distance_weight: "Вес отклонения от цели",
        settings_night_weight: "Вес ночных смен",
        settings_split_weight: "Вес сплит-смен",
        settings_save_generation: "Сохранить настройки генерации",
        settings_msg_failed_load_generation: "Не удалось загрузить настройки генерации.",
        settings_msg_failed_save_generation: "Не удалось сохранить настройки генерации.",
        settings_msg_generation_saved: "Настройки генерации сохранены.",
        settings_appearance_title: "Внешний вид",
        settings_appearance_text: "Настройте цвета расписания, чтобы карточки смен было проще различать.",
        settings_appearance_preview: "Предпросмотр",
        settings_color_morning: "Карточки утра",
        settings_color_morning_text: "Используется для утренних смен и легенды.",
        settings_color_evening: "Карточки вечера",
        settings_color_evening_text: "Используется для вечерних смен и легенды.",
        settings_color_night: "Карточки ночи",
        settings_color_night_text: "Используется для ночных смен и легенды.",
        settings_color_status: "Карточки статусов",
        settings_color_status_text: "Используется для выходных и специальных статусов.",
        settings_save_appearance: "Сохранить внешний вид",
        settings_msg_failed_save_appearance: "Не удалось сохранить настройки внешнего вида.",
        settings_msg_appearance_saved: "Настройки внешнего вида сохранены.",

        settings_notes_title: "Заметки",
        settings_note_1: "Эти разделы административные и обычно настраиваются реже, чем недельное расписание.",
        settings_note_2: "Основной еженедельный рабочий процесс всё равно начинается со страницы расписания.",
        settings_note_3: "При необходимости позже сюда можно добавить требования к сменам и настройки экспорта.",

        guide_page_title: "Руководство пользователя",
        guide_page_subtitle: "Простое объяснение, как подготовить сотрудников, собрать пожелания, создать расписание и выгрузить его.",
        guide_start_title: "Для чего нужно приложение",
        guide_start_text: "Schedule App помогает составлять рабочее расписание на неделю. Вы вносите сотрудников, должности, время смен, нужное количество людей и личные пожелания. После этого расписание можно создать автоматически или поправить вручную.",
        guide_setup_title: "Перед созданием расписания",
        guide_setup_text: "Основные данные заполняются один раз, а потом меняются только при необходимости.",
        guide_setup_step_1: "Откройте Сотрудники и добавьте всех людей, которые могут появляться в расписании.",
        guide_setup_step_2: "Откройте Настройки, затем Должности, и создайте роли, которые используются в отделении.",
        guide_setup_step_3: "Откройте Шаблоны смен и добавьте реальное время смен: утро, вечер, ночь или разделённые смены.",
        guide_setup_step_4: "Откройте Должности сотрудников и привяжите каждого сотрудника к ролям, в которых он может работать.",
        guide_setup_step_5: "Откройте Требования покрытия и укажите, сколько людей нужно в каждый промежуток времени.",
        guide_open_employees: "Открыть сотрудников",
        guide_open_settings: "Открыть настройки",
        guide_requests_title: "Соберите пожелания на неделю",
        guide_requests_text: "Перед планированием недели откройте Пожелания и отметьте выходные, отпуска, предпочтительные смены и ограничения. Так система не будет ставить людей туда, где они недоступны.",
        guide_open_requests: "Открыть пожелания",
        guide_schedule_title: "Создайте недельное расписание",
        guide_schedule_text: "Откройте Расписание, выберите неделю и должность, затем загрузите таблицу. Нажмите Автогенерация, если хотите, чтобы система заполнила смены. После этого проверьте предупреждения и внесите ручные изменения, если они нужны.",
        guide_schedule_step_1: "Выберите первый день недели.",
        guide_schedule_step_2: "Выберите должность, для которой нужно составить расписание.",
        guide_schedule_step_3: "Нажмите Загрузить, чтобы увидеть текущее расписание.",
        guide_schedule_step_4: "Нажмите Автогенерация, если хотите заполнить недостающие смены.",
        guide_schedule_step_5: "Перед завершением проверьте предупреждения и строки покрытия.",
        guide_open_schedule: "Открыть расписание",
        guide_manual_title: "Ручные изменения",
        guide_manual_text: "Смены можно добавлять и удалять вручную. Также можно отметить болезнь, выходной или неявку. Используйте эти действия, когда реальная ситуация изменилась после составления расписания.",
        guide_export_title: "Передайте расписание",
        guide_export_text: "Когда неделя выглядит правильно, нажмите Экспорт Excel на странице Расписание. Файл можно распечатать, отправить или сохранить как недельный отчёт.",
        guide_help_title: "Если что-то выглядит неправильно",
        guide_help_step_1: "Проверьте, что сотрудник привязан к выбранной должности.",
        guide_help_step_2: "Проверьте, что сотрудник не заблокирован выходным, отпуском, болезнью или пожеланием.",
        guide_help_step_3: "Проверьте, что шаблон смены активен и в нём указано правильное время.",
        guide_help_step_4: "Проверьте Требования покрытия и убедитесь, что нужное количество людей указано правильно.",
        guide_contents_title: "На этой странице",
        guide_contents_text: "Используйте ссылки, чтобы перейти к нужной части.",
        guide_contents_start: "Назначение",
        guide_contents_setup: "Подготовка",
        guide_contents_requests: "Пожелания",
        guide_contents_schedule: "Расписание",
        guide_contents_manual: "Ручные изменения",
        guide_contents_export: "Экспорт",
        guide_contents_help: "Помощь",

        common_actions: "Действия",
        common_back: "Назад",
        common_reload: "Обновить",
        common_reset: "Сбросить",
        common_edit: "Изменить",
        common_delete: "Удалить",
        common_cancel: "Отмена",
        common_confirm: "Подтвердить",
        common_recovery_backup: "Резервная копия для восстановления",

        coverage_page_title: "Требования покрытия",
        coverage_page_subtitle: "Настройка потребности в персонале по временным интервалам и должностям.",
        coverage_rest_title: "Настройки отдыха",
        coverage_rest_subtitle: "Минимальные перерывы используются при ручной проверке и автогенерации.",
        coverage_rest_morning_evening: "Перерыв утро → вечер, минут",
        coverage_rest_night_evening: "Перерыв ночь → вечер, минут",
        coverage_save_rest_settings: "Сохранить настройки отдыха",
        coverage_display_mode: "Отображение покрытия в расписании",
        coverage_display_interval: "По временным интервалам",
        coverage_display_category: "По категориям смен",
        coverage_start_time: "Начало",
        coverage_end_time: "Конец",
        coverage_staff_required: "Сотрудники",
        coverage_women_required: "Женщины",
        coverage_men_required: "Мужчины",
        coverage_overnight: "Через ночь",
        coverage_add_button: "Добавить",
        coverage_update_button: "Обновить",
        coverage_table_id: "ID",
        coverage_table_time: "Время",
        coverage_empty_list: "Требований покрытия пока нет",
        coverage_msg_failed_load_rest: "Не удалось загрузить настройки отдыха.",
        coverage_msg_failed_save_rest: "Не удалось сохранить настройки отдыха.",
        coverage_msg_women_gt_staff: "Минимум женщин не может быть больше общего числа сотрудников.",
        coverage_msg_men_gt_staff: "Минимум мужчин не может быть больше общего числа сотрудников.",
        coverage_msg_gender_gt_staff: "Минимум женщин и мужчин не может быть больше общего числа сотрудников.",
        coverage_msg_failed_save: "Не удалось сохранить требование покрытия.",
        coverage_msg_failed_load: "Не удалось загрузить требования покрытия.",
        coverage_msg_confirm_delete: "Удалить требование покрытия?",
        coverage_msg_failed_delete: "Не удалось удалить требование покрытия."
    },

    he: {
        app_title: "Schedule App",
        app_subtitle: "מערכת לסידור עבודה לצוות סיעודי",

        nav_section_main: "ראשי",
        nav_dashboard: "דף הבית",
        nav_schedule: "סידור עבודה",
        nav_employees: "עובדים",
        nav_requests: "העדפות",
        nav_settings: "הגדרות",

        sidebar_footer_title: "גרסה 0.13.3_beta",
        sidebar_footer_text: "כעת מתבצע עיצוב מחדש של הממשק. המטרה היא להפוך את תהליך העבודה לפשוט וברור יותר.",

        page_title: "דף הבית",
        page_subtitle: "מרכז שליטה נקי וברור יותר לניהול סידור העבודה השבועי.",

        home_title: "תפריט ראשי",
        home_subtitle: "בחר את הפעולה שאתה צריך עכשיו.",

        home_schedule_title: "יצירת סידור עבודה",
        home_schedule_text: "פתח את סידור העבודה השבועי וערוך או צור משמרות.",

        home_employees_title: "עובדים",
        home_employees_text: "הוספה, עריכה וניהול עובדים.",

        home_requests_title: "העדפות",
        home_requests_text: "סקירת העדפות שבועיות, ימי חופש והגבלות.",

        home_settings_title: "הגדרות",
        home_settings_text: "הגדרת תפקידים, תבניות משמרת ונתוני מערכת.",

        toggle_sidebar: "פתיחה או סגירה של התפריט",

        lang_he: "עברית",
        lang_en: "English",
        lang_ru: "Русский",

        hero_title: "סידור עבודה שבועי בלי עומס ויזואלי",
        hero_text: "הגרסה הזאת מתמקדת בבהירות, מהירות וחוויית עבודה מינימליסטית ונוחה יותר לשימוש יומיומי.",
        hero_open_schedule: "פתח סידור עבודה",
        hero_manage_employees: "ניהול עובדים",
        hero_system_settings: "הגדרות מערכת",

        stats_title: "השבוע הזה",
        stat_morning: "כיסוי בוקר",
        stat_evening: "כיסוי ערב",
        stat_night: "כיסוי לילה",
        stat_morning_value: "93%",
        stat_evening_value: "88%",
        stat_night_value: "100%",
        stat_morning_note: "כמעט מלא",
        stat_evening_note: "דורש תשומת לב",
        stat_night_note: "מכוסה במלואו",

        quick_actions_title: "פעולות מהירות",
        quick_action_schedule_title: "פתח את השבוע הנוכחי",
        quick_action_schedule_text: "מעבר ישיר לסידור העבודה השבועי והמשך עריכה.",
        quick_action_generate_title: "יצירה אוטומטית",
        quick_action_generate_text: "הפעלת האלגוריתם למילוי מהיר יותר של משמרות חסרות.",
        quick_action_export_title: "ייצוא לאקסל",
        quick_action_export_text: "הכנת סידור העבודה השבועי להדפסה ולשיתוף.",
        quick_action_requests_title: "בקשות עובדים",
        quick_action_requests_text: "סקירת העדפות, ימי חופש, חופשות והגבלות.",

        alerts_title: "התראות והערות",
        alert_1_title: "בוקר יום שלישי",
        alert_1_text: "עדיין חסר עובד אחד כדי להשלים את הכיסוי.",
        alert_2_title: "ערב יום רביעי",
        alert_2_text: "דרישת המינימום לנשים עדיין לא מולאה.",
        alert_3_title: "ליל שישי",
        alert_3_text: "משמרת הלילה מלאה ואינה דורשת שינוי.",

        summary_title: "אזור עבודה נוכחי",
        summary_week: "שבוע נבחר",
        summary_position: "תפקיד נבחר",
        summary_language: "שפת ממשק",
        summary_status: "סטטוס עיצוב מחדש",
        summary_status_value: "התשתית מוכנה",

        summary_badge: "תמיכה מלאה ב-RTL בעברית",
        schedule_workspace_ready_title: "מרחב העבודה של הסידור",
        schedule_workspace_ready_text: "בחר שבוע ותפקיד, ואז טען את הטבלה כדי להתחיל לערוך או ליצור.",
        schedule_no_positions_title: "לסידור העבודה נדרשים תפקידים",
        schedule_no_positions_text: "צור לפחות תפקיד אחד לפני טעינה או יצירה של סידור שבועי.",
        schedule_no_employees_title: "אין עובדים משויכים לתפקיד הזה",
        schedule_no_employees_text: "הוסף עובדים וקשר אותם לתפקיד הזה לפני מילוי השבוע.",
        schedule_action_load_hint: "יש לטעון קודם את השבוע והתפקיד שנבחרו.",
        schedule_action_generation_hint: "היצירה זמינה אחרי טעינת השבוע שנבחר.",
        schedule_action_export_hint: "הייצוא יהיה זמין אחרי טעינת השבוע שנבחר.",
        schedule_action_clear_hint: "ניקוי השבוע זמין אחרי טעינת השבוע שנבחר.",
        schedule_page_title: "סידור עבודה",
        schedule_page_subtitle: "ניהול סידור עבודה שבועי, הפעלת יצירה אוטומטית וייצוא התוצאה.",

        schedule_week_start: "תחילת שבוע",
        schedule_position: "תפקיד",
        schedule_select_position: "בחר תפקיד",

        schedule_load_btn: "טען",
        schedule_generate_btn: "יצירה אוטומטית",
        schedule_generate_all_btn: "יצירה לכולן",
        schedule_generating_title: "יוצר סידור עבודה",
        schedule_generating_text: "האלגוריתם בודק כיסוי, כללי מנוחה ומגבלות עובדים.",
        schedule_clear_btn: "נקה שבוע",
        schedule_export_btn: "ייצוא לאקסל",
        schedule_clear_message_btn: "נקה הודעה",
        schedule_toolbar_generate: "יצירה",
        schedule_toolbar_output: "פלט",
        schedule_toolbar_danger: "פעולות מסוכנות",
        schedule_status_legend: "סטטוס",
        schedule_status_week: "שבוע",
        schedule_status_position: "תפקיד",
        schedule_status_staff: "עובדים",
        schedule_status_shifts: "משמרות",
        schedule_status_gaps: "פערים",

        schedule_initial_hint: "בחר שבוע ותפקיד, ואז טען את סידור העבודה.",

        schedule_add_shift: "הוסף משמרת",
        schedule_select_shift_template: "בחר תבנית משמרת",
        schedule_add_shift_btn: "הוסף משמרת",

        schedule_day_status: "סטטוס יומי",
        schedule_no_status: "ללא סטטוס",
        schedule_save_status_btn: "שמור סטטוס",

        schedule_manual_day_status: "סטטוס יומי ידני",
        schedule_no_shifts_assigned: "לא הוקצו משמרות",
        schedule_other_positions_label: "תפקידים אחרים",
        schedule_delete_shift_btn: "מחק",

        schedule_employee_header: "עובד",
        schedule_coverage_header: "כיסוי",
        schedule_no_employees_for_position: "אין עובדים משויכים לתפקיד הזה.",

        employee_min_target_max: "מינימום/יעד/מקסימום",

        shift_morning: "בוקר",
        shift_evening: "ערב",
        shift_night: "לילה",

        status_sick: "מחלה",
        status_day_off: "יום חופשי",
        status_no_show: "אי הגעה",
        schedule_remove_status: "הסר סטטוס",
        schedule_shift_status: "סטטוס משמרת",
        schedule_status_sick_hint: "חוסם את כל תא היום",
        schedule_status_day_off_hint: "מסמן את כל היום כיום חופשי",
        schedule_no_shifts_for_no_show: "אין משמרות זמינות לסימון אי הגעה",

        coverage_staff: "עובדים",
        coverage_women: "נשים",
        coverage_men: "גברים",
        coverage_intervals_short: "חלונות",

        weekday_sunday: "יום ראשון",
        weekday_monday: "יום שני",
        weekday_tuesday: "יום שלישי",
        weekday_wednesday: "יום רביעי",
        weekday_thursday: "יום חמישי",
        weekday_friday: "יום שישי",
        weekday_saturday: "שבת",

        msg_failed_load_positions: "טעינת התפקידים נכשלה.",
        msg_server_error_load_positions: "שגיאת שרת בזמן טעינת התפקידים.",

        msg_select_week_start: "אנא בחר תאריך תחילת שבוע.",
        msg_select_position: "אנא בחר תפקיד.",

        msg_failed_load_schedule_data: "טעינת נתוני סידור העבודה נכשלה.",
        msg_server_error_load_schedule: "שגיאת שרת בזמן טעינת סידור העבודה.",
        msg_schedule_loaded: "סידור העבודה נטען בהצלחה.",
        msg_failed_save_schedule_display: "שמירת מצב תצוגת הכיסוי נכשלה.",

        msg_auto_generate_failed: "היצירה האוטומטית נכשלה.",
        msg_auto_generate_done: "היצירה האוטומטית הסתיימה.",
        schedule_generate_all_done: "היצירה האוטומטית לכל התפקידים הסתיימה.",
        schedule_generate_all_success_summary: "תפקידים שנוצרו",
        schedule_generate_all_created_summary: "משמרות שנוצרו",
        schedule_generate_all_failures_prefix: "תפקידים שנכשלו",
        msg_created_count: "נוצרו",
        msg_optimization_moved: "העברות שעברו אופטימיזציה",
        msg_warnings: "אזהרות",
        msg_server_error_auto_generate: "שגיאת שרת בזמן יצירה אוטומטית של סידור העבודה.",
        generation_summary_title: "סיכום יצירה",
        generation_summary_subtitle: "תוצאת היצירה האוטומטית האחרונה עבור השבוע והתפקיד שנבחרו.",
        generation_summary_clear_btn: "נקה סיכום",
        generation_summary_open_panel: "תוצאת היצירה המפורטת מוצגת בפאנל הסיכום.",
        generation_created_note: "רשומות חדשות שנוספו לסידור העבודה על ידי היצירה האוטומטית.",
        generation_optimized_note: "רשומות שנוצרו הועברו מחדש לצורך איזון טוב יותר.",
        generation_day_off_count: "ימי חופש שנוצרו",
        generation_day_off_note: "סטטוסי יום חופשי שנוצרו אוטומטית עבור ימים לא מכוסים של עובדים.",
        generation_hard_note: "בעיות חוסמות שנמצאו בבדיקה המקדימה.",
        generation_soft_note: "אזהרות שלא עצרו את היצירה.",
        generation_unfilled_note: "פערי כיסוי שנשארו לאחר היצירה.",
        generation_run_overview: "סקירת הרצה",
        generation_summary_week: "שבוע",
        generation_summary_position: "תפקיד",
        generation_summary_status: "סטטוס ישימות",
        generation_feasibility_status_ok: "תקין",
        generation_feasibility_status_blocking: "חוסם",
        generation_unfilled_title: "דרישות שלא מולאו",
        generation_summary_clean_title: "תוצאת יצירה נקייה",
        generation_summary_clean_text: "ההרצה הסתיימה ללא אזהרות, ללא חסימות קשיחות וללא דרישות כיסוי שנותרו פתוחות.",
        generation_missing_total: "חסר סך הכל",
        generation_missing_female: "חסרות נשים",
        generation_missing_male: "חסרים גברים",
        generation_reasons: "סיבות",

        msg_confirm_clear_week: "האם אתה בטוח שברצונך למחוק את סידור העבודה של השבוע הזה עבור התפקיד הזה?",
        msg_confirm_clear_week_title: "ניקוי סידור עבודה שבועי",
        msg_failed_clear_week: "ניקוי סידור העבודה השבועי נכשל.",
        msg_week_cleared: "סידור העבודה השבועי נוקה.",
        msg_deleted_count: "נמחקו",
        confirm_impact_position: "תפקיד",
        confirm_impact_employee: "עובד",
        confirm_impact_template: "תבנית",
        confirm_impact_assignment: "שיוך",
        confirm_impact_week: "שבוע",
        confirm_impact_schedule_entries: "רשומות סידור עבודה",
        confirm_impact_assignments: "שיוכים",
        confirm_impact_general_preferences: "העדפות כלליות",
        confirm_impact_weekly_preferences: "העדפות שבועיות",
        confirm_impact_day_statuses: "סטטוסי יום",
        confirm_impact_day_off_statuses: "סטטוסי יום חופשי",
        confirm_impact_shift_requirements: "דרישות משמרת",
        confirm_impact_coverage_requirements: "דרישות כיסוי",
        confirm_impact_assigned_employees: "עובדים משויכים",
        confirm_impact_in_use_warning: "התבנית הזו כבר נמצאת בשימוש בסידור העבודה, ולכן המחיקה תיחסם.",
        confirm_impact_fetch_failed: "לא ניתן היה לטעון את הרשומות הקשורות. בדוק את ההשפעה לפני המחיקה.",
        msg_server_error_clear_week: "שגיאת שרת בזמן ניקוי השבוע.",

        msg_select_shift_template_first: "אנא בחר קודם תבנית משמרת.",
        msg_status_selector_not_found: "בורר הסטטוס לא נמצא.",

        msg_failed_add_shift: "הוספת המשמרת נכשלה.",
        msg_shift_added: "המשמרת נוספה בהצלחה.",
        msg_server_error_add_shift: "שגיאת שרת בזמן הוספת משמרת.",

        msg_failed_delete_shift: "מחיקת המשמרת נכשלה.",
        msg_shift_deleted: "המשמרת נמחקה בהצלחה.",
        msg_server_error_delete_shift: "שגיאת שרת בזמן מחיקת משמרת.",

        msg_failed_save_day_status: "שמירת סטטוס היום נכשלה.",
        msg_day_status_saved: "סטטוס היום נשמר בהצלחה.",
        msg_server_error_save_day_status: "שגיאת שרת בזמן שמירת סטטוס היום.",
        msg_failed_save_shift_status: "שמירת סטטוס המשמרת נכשלה.",
        msg_no_show_saved: "סטטוס אי ההגעה נשמר בהצלחה.",
        msg_no_show_removed: "סטטוס אי ההגעה הוסר בהצלחה.",
        msg_server_error_save_shift_status: "שגיאת שרת בזמן שמירת סטטוס המשמרת.",

        generation_warning_no_active_slots_week: "אין מקטעי כיסוי פעילים לשבוע הזה",
        generation_warning_no_active_slots_day: "אין מקטעי כיסוי פעילים ליום הזה",
        generation_warning_emergency_fatigue: "נעשה שימוש חריג בהקלה על כללי עייפות כדי לכסות מקטע",
        generation_warning_underfilled: "לא מולא במלואו",
        generation_warning_reasons: "סיבות:",
        generation_warning_worked_days: "עבד ימים ללא יום מנוחה שבועי חובה",
        generation_warning_consecutive_nights: "ימי לילה רצופים",
        generation_warning_consecutive_splits: "ימי משמרות מפוצלות רצופים",
        generation_reason_not_enough_female: "אין מספיק עובדות זמינות",
        generation_reason_not_enough_male: "אין מספיק עובדים זמינים",
        generation_reason_split_pair: "לתבנית מפוצלת אין זוג תקין",
        generation_reason_day_status: "סטטוס היום חוסם את העובד",
        generation_reason_not_assigned: "העובד אינו משויך לתפקיד הזה",
        generation_reason_max_shifts: "העובד הגיע למקסימום המשמרות",
        generation_reason_weekly_max_shifts: "העובד הגיע למקסימום המשמרות השבועי",
        generation_reason_preference_or_permission: "העדפות או הרשאות העובד חוסמות את המשמרת הזו",
        generation_reason_mandatory_day_off: "יום המנוחה השבועי החובה יופר",
        generation_reason_overlapping_shift: "לעובד כבר יש משמרת חופפת",
        generation_reason_cannot_split_day: "העובד אינו יכול לעבוד בוקר וערב באותו יום",
        generation_reason_unpairable_shift_type: "לעובד כבר יש סוג משמרת אחר שלא ניתן לשלב",
        generation_reason_split_only_combo: "שילוב בוקר-ערב דורש תבניות מפוצלות בלבד",
        generation_reason_weekly_preference_split: "העדפה שבועית חוסמת שילוב בוקר-ערב",
        generation_reason_two_shifts_day: "לעובד כבר יש שתי משמרות באותו יום",
        generation_reason_off_or_vacation: "לעובד יש יום חופשי או חופשה",
        generation_reason_preference_conflict: "המשמרת מתנגשת עם העדפת העובד",
        generation_reason_morning_after_night: "בוקר אחרי לילה אסור",
        generation_reason_night_evening_rest: "אין מספיק מנוחה אחרי לילה לפני ערב",
        generation_reason_morning_evening_rest: "אין מספיק מנוחה בין בוקר לערב",
        generation_reason_weekly_day_off: "יום המנוחה השבועי החובה יופר",
        generation_reason_consecutive_nights: "הגיע למגבלת לילות רצופים",
        generation_reason_consecutive_splits: "הגיע למגבלת משמרות מפוצלות רצופות",
        generation_reason_too_many_consecutive_nights: "יותר מדי משמרות לילה רצופות",
        generation_reason_too_many_consecutive_splits: "יותר מדי משמרות מפוצלות רצופות",
        generation_reason_no_coverage_gain: "היו מועמדים, אך הם לא שיפרו את הכיסוי בלי עודף במקטעים אחרים",
        generation_precheck_blocking: "בדיקה מוקדמת, בעיה חוסמת:",
        generation_precheck_warning: "בדיקה מוקדמת, אזהרה:",
        generation_precheck_no_slots: "לא ניתן לבנות מקטעי כיסוי פעילים מדרישות הכיסוי.",
        generation_precheck_no_template: "אין תבנית משמרת פעילה שמכסה את המקטע הנדרש הזה.",
        generation_precheck_no_legacy_template: "אין תבנית פעילה שאינה מפוצלת עבור דרישת המשמרת הזו.",
        generation_precheck_staff_shortage: "נדרשים יותר עובדים ממספר העובדים המשויכים לתפקיד.",
        generation_precheck_female_shortage: "נדרשות יותר נשים ממספר העובדות הזמינות.",
        generation_precheck_male_shortage: "נדרשים יותר גברים ממספר העובדים הזמינים.",
        generation_precheck_no_candidate: "אין מועמד מתאים של עובד/תבנית לכיסוי המקטע הזה.",
        generation_precheck_emergency_only: "המקטע הזה ניתן לכיסוי רק עם הקלה חריגה בכללי עייפות.",
        generation_hard_constraints: "אילוצים קשיחים",
        generation_soft_constraints: "אילוצים רכים",
        generation_unfilled_count: "דרישות שלא כוסו",
        generation_hard_short: "קשיח",
        generation_soft_short: "רך",
        generation_unfilled_short: "פער",

        msg_failed_refresh_schedule_data: "רענון נתוני סידור העבודה נכשל.",
        msg_server_error_refresh_schedule_data: "שגיאת שרת בזמן רענון נתוני סידור העבודה.",
        employees_page_title: "עובדים",
        employees_page_subtitle: "יצירה, עריכה וניהול נתוני עובדים המשמשים לסידור עבודה.",

        employees_form_title: "טופס עובד",
        employees_form_subtitle: "מלא את פרטי העובד ושמור אותם במערכת.",

        employees_full_name: "שם מלא",
        employees_full_name_placeholder: "הזן שם מלא",

        employees_sex: "מין",
        employees_select_sex: "בחר מין",
        employees_sex_male: "זכר",
        employees_sex_female: "נקבה",

        employees_min_shifts: "מינימום משמרות / שבוע",
        employees_target_shifts: "יעד משמרות / שבוע",
        employees_max_shifts: "מקסימום משמרות / שבוע",
        employees_shift_limits_hint: "ודא שערכי המינימום, היעד והמקסימום תואמים זה לזה מבחינה לוגית.",

        employees_rules_title: "כללי זמינות",
        employees_can_work_night: "יכול לעבוד במשמרות לילה",
        employees_can_work_weekends: "יכול לעבוד בסופי שבוע",
        employees_can_work_evenings_after_night: "יכול לעבוד ערב אחרי משמרת לילה",
        employees_can_work_mornings_and_evenings: "יכול לעבוד בוקר וערב באותו יום",

        employees_add_button: "הוסף עובד",
        employees_update_button: "עדכן עובד",

        employees_list_title: "רשימת עובדים",
        employees_list_subtitle: "העובדים הקיימים כרגע במערכת.",

        footer_docs: "תיעוד",
        footer_guide: "מדריך",
        footer_version: "Schedule App v0.13.3_beta",

        employees_table_id: "מזהה",
        employees_table_name: "שם מלא",
        employees_table_sex: "מין",
        employees_table_min_target_max: "מינימום / יעד / מקסימום",
        employees_table_night: "לילה",
        employees_table_weekends: "סופי שבוע",
        employees_table_evening_after_night: "ערב אחרי לילה",
        employees_table_morning_evening: "בוקר + ערב",
        employees_table_actions: "פעולות",

        settings_help_label: "צריך עזרה?",
        settings_docs_link: "תיעוד",
        settings_guide_link: "מדריך משתמש",
        settings_backup_title: "בטיחות מסד הנתונים",
        settings_backup_text: "צור גיבויים ידניים ושחזר גיבוי אחרון אם צריך לבטל פעולה הרסנית.",
        settings_backup_create: "צור גיבוי",
        settings_backup_upload_label: "העלה ושחזר",
        settings_backup_name: "גיבוי",
        settings_backup_modified: "עודכן",
        settings_backup_size: "גודל",
        settings_backup_actions: "פעולות",
        settings_backup_empty: "עדיין אין גיבויים",
        settings_backup_restore: "שחזר",
        settings_backup_created: "הגיבוי נוצר",
        settings_backup_restored: "הגיבוי שוחזר",
        settings_backup_pre_restore: "מסד הנתונים הנוכחי נשמר בשם",
        settings_backup_load_failed: "טעינת הגיבויים נכשלה.",
        settings_backup_create_failed: "יצירת הגיבוי נכשלה.",
        settings_backup_restore_failed: "שחזור הגיבוי נכשל.",
        settings_backup_restore_confirm: "לשחזר את הגיבוי הזה ולהחליף את מסד הנתונים הנוכחי?",
        settings_backup_empty_title: "עדיין אין גיבויים",
        settings_backup_empty_text: "צור גיבוי ידני לפני ניקוי גדול או פעולות מחיקה.",
        employees_empty_state_title: "עדיין אין עובדים",
        employees_empty_state_text: "הוסף את העובד הראשון כדי לפתוח שיוכים, העדפות שבועיות וסידור עבודה.",
        positions_empty_state_title: "עדיין אין תפקידים",
        positions_empty_state_text: "הוסף את התפקיד הראשון לפני שיוך עובדים או הגדרת כיסוי.",
        templates_empty_state_title: "עדיין אין תבניות משמרת",
        templates_empty_state_text: "צור תבניות משמרת לפני יצירה אוטומטית או עריכה ידנית של הסידור.",
        assignments_empty_state_title: "עדיין אין שיוכים",
        assignments_empty_state_text: "קשר עובדים לתפקידים כדי שיוכלו להופיע בסידור העבודה.",
        assignments_missing_prereq_title: "לשיוכים נדרשים עובדים ותפקידים",
        assignments_missing_prereq_text: "צור קודם עובדים ותפקידים, ואז חזור לכאן כדי לקשר ביניהם.",
        coverage_empty_state_title: "עדיין אין דרישות כיסוי",
        coverage_empty_state_text: "הוסף דרישות כוח אדם לפי זמן אחרי שהתפקידים מוכנים.",
        coverage_missing_positions_title: "לדרישות הכיסוי נדרשים תפקידים",
        coverage_missing_positions_text: "צור לפחות תפקיד אחד לפני הוספת דרישות כוח אדם.",
        preferences_empty_initial_title: "עדיין לא נטען שבוע",
        preferences_empty_initial_text: "בחר שבוע ועובד כדי לעיין או לעדכן העדפות שבועיות.",
        preferences_empty_no_employees_title: "אין עובדים זמינים",
        preferences_empty_no_employees_text: "הוסף עובדים לפני איסוף העדפות שבועיות.",
        common_open_employees: "פתח עובדים",
        common_open_positions: "פתח תפקידים",
        common_open_assignments: "פתח שיוכים",

        employees_empty_list: "אין עדיין עובדים",

        employees_edit_button: "ערוך",
        employees_delete_button: "מחק",
        msg_failed_load_employees: "טעינת העובדים נכשלה.",
        msg_server_error_load_employees: "שגיאת שרת בזמן טעינת העובדים.",
        msg_enter_employee_full_name: "אנא הזן שם מלא.",
        msg_select_employee_sex: "אנא בחר מין.",
        msg_min_gt_max_shifts: "מינימום המשמרות לא יכול להיות גדול מהמקסימום.",
        msg_target_lt_min_shifts: "יעד המשמרות לא יכול להיות קטן מהמינימום.",
        msg_target_gt_max_shifts: "יעד המשמרות לא יכול להיות גדול מהמקסימום.",
        msg_employee_operation_failed: "הפעולה נכשלה.",
        msg_server_error_save_employee: "שגיאת שרת בזמן שמירת העובד.",
        msg_editing_employee: "עורך עובד",
        msg_confirm_delete_employee: "האם אתה בטוח שברצונך למחוק את העובד הזה?",
        msg_failed_delete_employee: "מחיקת העובד נכשלה.",
        msg_server_error_delete_employee: "שגיאת שרת בזמן מחיקת העובד.",
        msg_confirm_delete_position: "האם אתה בטוח שברצונך למחוק את התפקיד הזה?",
        msg_failed_delete_position: "מחיקת התפקיד נכשלה.",
        msg_server_error_delete_position: "שגיאת שרת בזמן מחיקת התפקיד.",

        employees_notes_title: "הערות",
        employees_note_1: "עובדים אלו משמשים בהמשך בדף יצירת סידור העבודה.",
        employees_note_2: "בעתיד עובד אחד יכול להיות משויך למספר תפקידים.",
        employees_note_3: "הטבלה כאן היא ניהולית, בעוד שדף סידור העבודה הוא מסך העבודה הראשי.",

        common_yes: "כן",
        common_no: "לא",
        preferences_page_title: "העדפות שבועיות",
        preferences_page_subtitle: "הגדרת העדפות שבועיות של עובדים, הגבלות וכללים לפי ימים.",

        preferences_week_start: "תחילת שבוע",
        preferences_employee: "עובד",
        preferences_select_employee: "בחר עובד",

        preferences_load_btn: "טען",
        preferences_save_btn: "שמור",

        preferences_initial_hint: "בחר שבוע ועובד, ואז לחץ על טען.",

        preferences_day_column: "יום",
        preferences_date_column: "תאריך",
        preferences_value_column: "העדפה",

        preferences_employee_not_found: "העובד לא נמצא",

        preferences_notes_title: "הערות",
        preferences_note_1: "העדפות נשמרות לכל עובד ולכל תאריך בנפרד.",
        preferences_note_2: "ערכים אלו משפיעים על יצירת סידור העבודה ועל בדיקה ידנית.",
        preferences_note_3: "בפרויקט הזה השבוע מתחיל ביום ראשון.",

        preference_no_preference: "ללא העדפה",
        preference_off_day: "יום חופשי",
        preference_only_morning: "רק בוקר",
        preference_vacation: "חופשה",
        preference_only_evening: "רק ערב",
        preference_only_night: "רק לילה",
        preference_not_morning: "לא בוקר",
        preference_not_evening: "לא ערב",
        preference_not_night: "לא לילה",
        preference_no_morning_evening_combo: "ללא שילוב בוקר + ערב",

        msg_select_employee: "אנא בחר עובד.",
        msg_failed_load_preferences: "טעינת ההעדפות נכשלה.",
        msg_server_error_load_preferences: "שגיאת שרת בזמן טעינת ההעדפות.",
        msg_preferences_loaded: "ההעדפות נטענו בהצלחה.",
        msg_nothing_to_save: "אין מה לשמור.",
        msg_some_preferences_not_saved: "חלק מההעדפות לא נשמרו.",
        msg_preferences_saved: "ההעדפות נשמרו בהצלחה.",
        msg_server_error_save_preferences: "שגיאת שרת בזמן שמירת ההעדפות.",
        positions_page_title: "תפקידים",
        positions_page_subtitle: "יצירה וניהול תפקידי מחלקה המשמשים את מערכת סידור העבודה.",

        positions_form_title: "טופס תפקיד",
        positions_form_subtitle: "הוסף תפקיד חדש והגדר מאפיינים הקשורים לכיסוי.",

        positions_name: "שם התפקיד",
        positions_name_placeholder: "לדוגמה: אחות",

        positions_coverage_title: "הגדרות כיסוי",
        positions_requires_continuous_coverage: "דורש כיסוי רציף",
        positions_minimum_staff_presence: "מינימום עובדים נוכחים בכל רגע",
        positions_minimum_staff_presence_hint: "הגדר זאת רק אם נדרש כיסוי רציף.",

        positions_add_button: "הוסף תפקיד",

        positions_list_title: "רשימת תפקידים",
        positions_list_subtitle: "כל התפקידים השמורים כרגע במערכת.",
        positions_reload_button: "טען מחדש",

        positions_table_id: "מזהה",
        positions_table_name: "שם",
        positions_table_continuous: "כיסוי רציף",
        positions_table_min_presence: "מינימום נוכחות",

        positions_empty_list: "אין עדיין תפקידים",

        positions_notes_title: "הערות",
        positions_note_1: "בהמשך ניתן לשייך תפקיד אחד למספר עובדים.",
        positions_note_2: "כיסוי רציף שימושי לתפקידים הדורשים נוכחות קבועה.",
        positions_note_3: "מינימום נוכחות בדרך כלל צריך להישאר 0 אלא אם כיסוי רציף מופעל.",

        msg_enter_position_name: "אנא הזן שם תפקיד.",
        msg_failed_add_position: "הוספת התפקיד נכשלה.",
        msg_server_error_save_position: "שגיאת שרת בזמן שמירת התפקיד.",
        templates_page_title: "תבניות משמרת",
        templates_page_subtitle: "יצירה וניהול תבניות משמרת לשימוש ביצירה אוטומטית ובהקצאה ידנית.",

        templates_form_title: "טופס תבנית משמרת",
        templates_form_subtitle: "הוסף או ערוך תבנית משמרת ששייכת לתפקיד אחד.",

        templates_name: "שם התבנית",
        templates_name_placeholder: "לדוגמה: בוקר 06:30-13:30",
        templates_category: "קטגוריית משמרת",
        templates_select_category: "בחר קטגוריה",

        templates_start_time: "שעת התחלה",
        templates_end_time: "שעת סיום",

        templates_flags_title: "אפשרויות תבנית",
        templates_is_overnight: "משמרת שחוצה ליום הבא",
        templates_is_active: "תבנית פעילה",
        templates_is_split_only: "רק למשמרות מפוצלות",

        templates_add_button: "הוסף תבנית משמרת",
        templates_update_button: "עדכן תבנית משמרת",

        templates_list_title: "רשימת תבניות",
        templates_list_subtitle: "כל תבניות המשמרת השמורות במערכת, לפי תפקיד.",
        templates_reload_button: "טען מחדש",

        templates_table_id: "מזהה",
        templates_table_name: "שם",
        templates_table_category: "קטגוריה",
        templates_table_start: "התחלה",
        templates_table_end: "סיום",
        templates_table_overnight: "חוצה לילה",
        templates_table_active: "פעילה",
        templates_table_split_only: "רק מפוצלת",
        templates_table_actions: "פעולות",

        templates_empty_list: "אין עדיין תבניות משמרת",

        templates_edit_button: "ערוך",
        templates_delete_button: "מחק",

        templates_notes_title: "הערות",
        templates_note_1: "הקטגוריה מגדירה את התפקיד הלוגי של המשמרת: בוקר, ערב או לילה.",
        templates_note_2: "משמרת שחוצה ליום הבא מסתיימת ביום שלאחר מכן.",
        templates_note_3: "תבניות שמיועדות רק למשמרות מפוצלות נועדו לזוגות של משמרות מפוצלות ולא לשימוש בודד.",

        msg_enter_template_name: "אנא הזן שם תבנית.",
        msg_select_shift_category: "אנא בחר קטגוריית משמרת.",
        msg_enter_start_end_time: "אנא הזן שעת התחלה ושעת סיום.",
        msg_failed_save_template: "שמירת תבנית המשמרת נכשלה.",
        msg_server_error_save_template: "שגיאת שרת בזמן שמירת תבנית המשמרת.",

        msg_editing_template: "עורך תבנית",
        msg_confirm_delete_template: "האם אתה בטוח שברצונך למחוק את תבנית המשמרת הזאת?",
        msg_failed_delete_template: "מחיקת תבנית המשמרת נכשלה.",
        msg_server_error_delete_template: "שגיאת שרת בזמן מחיקת תבנית המשמרת.",

        msg_failed_load_templates: "טעינת תבניות המשמרת נכשלה.",
        msg_server_error_load_templates: "שגיאת שרת בזמן טעינת תבניות המשמרת.",
        assignments_page_title: "שיוכים",
        assignments_page_subtitle: "שייך עובדים לתפקידים ונהל את עדיפותם בסידור העבודה.",

        assignments_form_title: "טופס שיוך",
        assignments_form_subtitle: "חבר עובד אחד לתפקיד אחד והגדר אפשרויות עדיפות.",

        assignments_employee: "עובד",
        assignments_position: "תפקיד",
        assignments_select_employee: "בחר עובד",
        assignments_select_position: "בחר תפקיד",

        assignments_priority_score: "ציון עדיפות",
        assignments_priority_hint: "ערכים גבוהים יותר יכולים לשמש להעדפת העובד הזה עבור התפקיד הזה.",

        assignments_options_title: "אפשרויות שיוך",
        assignments_is_primary: "תפקיד ראשי עבור העובד הזה",
        assignments_is_fallback_only: "לשימוש כגיבוי בלבד",

        assignments_add_button: "שייך תפקיד",

        assignments_list_title: "רשימת שיוכים",
        assignments_list_subtitle: "כל הקישורים עובד-תפקיד השמורים כרגע במערכת.",
        assignments_reload_button: "טען מחדש",

        assignments_table_employee: "עובד",
        assignments_table_position: "תפקיד",
        assignments_table_primary: "ראשי",
        assignments_table_priority: "עדיפות",
        assignments_table_fallback: "גיבוי בלבד",
        assignments_table_actions: "פעולות",

        assignments_empty_list: "אין עדיין שיוכים",
        assignments_delete_button: "הסר",

        assignments_notes_title: "הערות",
        assignments_note_1: "עובד אחד יכול להיות משויך למספר תפקידים.",
        assignments_note_2: "דף סידור העבודה משתמש בשיוכים אלה כדי לקבוע מי יכול לעבוד בכל תפקיד.",
        assignments_note_3: "הסרת שיוך מוחקת גם את רשומות סידור העבודה הקשורות לאותו עובד ותפקיד.",

        msg_failed_load_assignment_data: "טעינת נתוני השיוך נכשלה.",
        msg_server_error_load_assignment_data: "שגיאת שרת בזמן טעינת נתוני השיוך.",
        msg_failed_assign_position: "שיוך התפקיד נכשל.",
        msg_server_error_save_assignment: "שגיאת שרת בזמן שמירת השיוך.",
        msg_confirm_delete_assignment: "האם אתה בטוח שברצונך להסיר את השיוך הזה?",
        msg_failed_delete_assignment: "מחיקת השיוך נכשלה.",
        msg_server_error_delete_assignment: "שגיאת שרת בזמן מחיקת השיוך.",
        settings_page_title: "הגדרות",
        settings_page_subtitle: "פתח ונהל את החלקים הניהוליים של מערכת סידור העבודה.",

        settings_positions_title: "תפקידים",
        settings_positions_text: "יצירה וניהול תפקידי מחלקה המשמשים את מערכת סידור העבודה.",

        settings_templates_title: "תבניות משמרת",
        settings_templates_text: "צור תבניות משמרת נפרדות לכל תפקיד.",

        settings_assignments_title: "שיוכים",
        settings_assignments_text: "שייך עובדים לתפקידים והגדר עדיפות או שימוש כגיבוי.",

        settings_coverage_title: "דרישות כיסוי",
        settings_coverage_text: "הגדר כמה עובדים נדרשים בכל טווח זמן.",
        settings_generation_title: "כללי יצירה",
        settings_generation_text: "הגדר מגבלות חירום והתנהגות משמרות בין תפקידים עבור יצירה אוטומטית.",
        settings_allow_multiple_positions_per_day: "אפשר כמה תפקידים באותו יום",
        settings_max_work_days: "מקסימום ימי עבודה בשבוע",
        settings_max_nights: "מקסימום לילות רצופים",
        settings_emergency_nights: "מגבלת חירום ללילות",
        settings_max_splits: "מקסימום ימי פיצול רצופים",
        settings_emergency_splits: "מגבלת חירום לפיצולים",
        settings_night_evening_penalty: "קנס לילה → ערב",
        settings_shortage_weight: "משקל חוסר בכיסוי",
        settings_gender_bonus_weight: "בונוס יעד מגדר",
        settings_missing_min_weight: "משקל חוסר במינימום משמרות",
        settings_target_distance_weight: "משקל סטייה מהיעד",
        settings_night_weight: "משקל משמרות לילה",
        settings_split_weight: "משקל משמרות מפוצלות",
        settings_save_generation: "שמור הגדרות יצירה",
        settings_msg_failed_load_generation: "טעינת הגדרות היצירה נכשלה.",
        settings_msg_failed_save_generation: "שמירת הגדרות היצירה נכשלה.",
        settings_msg_generation_saved: "הגדרות היצירה נשמרו.",
        settings_appearance_title: "מראה",
        settings_appearance_text: "התאם את צבעי הסידור כדי לזהות משמרות בקלות רבה יותר.",
        settings_appearance_preview: "תצוגה מקדימה",
        settings_color_morning: "כרטיסי בוקר",
        settings_color_morning_text: "משמש לכרטיסי משמרת בוקר ולמקרא.",
        settings_color_evening: "כרטיסי ערב",
        settings_color_evening_text: "משמש לכרטיסי משמרת ערב ולמקרא.",
        settings_color_night: "כרטיסי לילה",
        settings_color_night_text: "משמש לכרטיסי משמרת לילה ולמקרא.",
        settings_color_status: "כרטיסי סטטוס",
        settings_color_status_text: "משמש לימי חופש ולסטטוסים מיוחדים.",
        settings_save_appearance: "שמור מראה",
        settings_msg_failed_save_appearance: "שמירת הגדרות המראה נכשלה.",
        settings_msg_appearance_saved: "הגדרות המראה נשמרו.",

        settings_notes_title: "הערות",
        settings_note_1: "החלקים האלה ניהוליים ובדרך כלל מוגדרים בתדירות נמוכה יותר מאשר סידור העבודה השבועי.",
        settings_note_2: "תהליך העבודה השבועי הראשי עדיין מתחיל מדף סידור העבודה.",
        settings_note_3: "אם יהיה צורך בהמשך, ניתן להוסיף לעמוד הזה גם דרישות משמרת והגדרות ייצוא.",

        guide_page_title: "מדריך משתמש",
        guide_page_subtitle: "הסבר פשוט על הכנת עובדים, איסוף העדפות, יצירת סידור עבודה וייצוא שלו.",
        guide_start_title: "למה האפליקציה מיועדת",
        guide_start_text: "Schedule App עוזרת לבנות סידור עבודה שבועי. מזינים עובדים, תפקידים, שעות משמרת, צרכי כוח אדם והעדפות אישיות. לאחר מכן אפשר ליצור את הסידור אוטומטית או לתקן אותו ידנית.",
        guide_setup_title: "לפני יצירת סידור עבודה",
        guide_setup_text: "ממלאים את המידע הבסיסי פעם אחת, ואז מעדכנים אותו רק כשמשהו משתנה.",
        guide_setup_step_1: "פתח את עובדים והוסף כל אדם שיכול להופיע בסידור העבודה.",
        guide_setup_step_2: "פתח את הגדרות, לאחר מכן תפקידים, וצור את התפקידים שמשמשים במחלקה.",
        guide_setup_step_3: "פתח את תבניות משמרת והוסף את זמני המשמרות האמיתיים, כמו בוקר, ערב, לילה או משמרות מפוצלות.",
        guide_setup_step_4: "פתח את שיוך עובדים לתפקידים וחבר כל עובד לתפקידים שבהם הוא יכול לעבוד.",
        guide_setup_step_5: "פתח את דרישות כיסוי ורשום כמה עובדים נדרשים בכל טווח זמן.",
        guide_open_employees: "פתח עובדים",
        guide_open_settings: "פתח הגדרות",
        guide_requests_title: "איסוף העדפות שבועיות",
        guide_requests_text: "לפני תכנון השבוע, פתח את העדפות וסמן ימי חופש, חופשות, משמרות מועדפות והגבלות. כך המערכת נמנעת משיבוץ אנשים כשהם לא זמינים.",
        guide_open_requests: "פתח העדפות",
        guide_schedule_title: "יצירת סידור העבודה השבועי",
        guide_schedule_text: "פתח את סידור עבודה, בחר שבוע ותפקיד, ואז טען את הטבלה. השתמש ביצירה אוטומטית כדי לתת למערכת למלא משמרות. לאחר מכן בדוק התראות ובצע שינויים ידניים לפי הצורך.",
        guide_schedule_step_1: "בחר את היום הראשון של השבוע.",
        guide_schedule_step_2: "בחר את התפקיד שעבורו רוצים לבנות סידור.",
        guide_schedule_step_3: "לחץ על טען כדי לראות את הסידור הנוכחי.",
        guide_schedule_step_4: "לחץ על יצירה אוטומטית אם רוצים למלא משמרות חסרות.",
        guide_schedule_step_5: "בדוק התראות ושורות כיסוי לפני סיום.",
        guide_open_schedule: "פתח סידור עבודה",
        guide_manual_title: "שינויים ידניים",
        guide_manual_text: "אפשר להוסיף או למחוק משמרות ידנית. אפשר גם לסמן עובד כחולה, ביום חופש או כאי הגעה. השתמש באפשרויות האלה כשהמצב בפועל משתנה אחרי יצירת הסידור.",
        guide_export_title: "שיתוף סידור העבודה",
        guide_export_text: "כשהשבוע נראה נכון, השתמש בייצוא לאקסל בדף סידור עבודה. הקובץ מיועד להדפסה, שליחה או שמירה כרשומה שבועית.",
        guide_help_title: "אם משהו נראה לא תקין",
        guide_help_step_1: "בדוק שהעובד משויך לתפקיד שנבחר.",
        guide_help_step_2: "בדוק שהעובד אינו חסום בגלל יום חופש, חופשה, מחלה או בקשה.",
        guide_help_step_3: "בדוק שתבנית המשמרת פעילה ושזמן המשמרת נכון.",
        guide_help_step_4: "בדוק את דרישות הכיסוי וודא שמספר העובדים הנדרש נכון.",
        guide_contents_title: "בעמוד זה",
        guide_contents_text: "השתמש בקישורים כדי לעבור לחלק הדרוש.",
        guide_contents_start: "מטרה",
        guide_contents_setup: "הכנה",
        guide_contents_requests: "העדפות",
        guide_contents_schedule: "סידור עבודה",
        guide_contents_manual: "שינויים ידניים",
        guide_contents_export: "ייצוא",
        guide_contents_help: "עזרה",

        common_actions: "פעולות",
        common_back: "חזרה",
        common_reload: "טען מחדש",
        common_reset: "איפוס",
        common_edit: "עריכה",
        common_delete: "מחיקה",
        common_cancel: "ביטול",
        common_confirm: "אישור",
        common_recovery_backup: "גיבוי שחזור",

        coverage_page_title: "דרישות כיסוי",
        coverage_page_subtitle: "דרישות כוח אדם לפי טווחי זמן ותפקידים.",
        coverage_rest_title: "הגדרות מנוחה",
        coverage_rest_subtitle: "הגדרת זמני מנוחה מינימליים לבדיקה ידנית וליצירה אוטומטית.",
        coverage_rest_morning_evening: "מנוחה מבוקר לערב, דקות",
        coverage_rest_night_evening: "מנוחה מלילה לערב, דקות",
        coverage_save_rest_settings: "שמור הגדרות מנוחה",
        coverage_display_mode: "תצוגת כיסוי בסידור העבודה",
        coverage_display_interval: "לפי טווחי זמן",
        coverage_display_category: "לפי קטגוריות משמרת",
        coverage_start_time: "התחלה",
        coverage_end_time: "סיום",
        coverage_staff_required: "עובדים",
        coverage_women_required: "נשים",
        coverage_men_required: "גברים",
        coverage_overnight: "חוצה לילה",
        coverage_add_button: "הוסף",
        coverage_update_button: "עדכן",
        coverage_table_id: "ID",
        coverage_table_time: "זמן",
        coverage_empty_list: "אין עדיין דרישות כיסוי",
        coverage_msg_failed_load_rest: "טעינת הגדרות המנוחה נכשלה.",
        coverage_msg_failed_save_rest: "שמירת הגדרות המנוחה נכשלה.",
        coverage_msg_women_gt_staff: "מינימום הנשים לא יכול להיות גדול מסך העובדים.",
        coverage_msg_men_gt_staff: "מינימום הגברים לא יכול להיות גדול מסך העובדים.",
        coverage_msg_gender_gt_staff: "מינימום הנשים והגברים לא יכול להיות גדול מסך העובדים.",
        coverage_msg_failed_save: "שמירת דרישת הכיסוי נכשלה.",
        coverage_msg_failed_load: "טעינת דרישות הכיסוי נכשלה.",
        coverage_msg_confirm_delete: "למחוק את דרישת הכיסוי?",
        coverage_msg_failed_delete: "מחיקת דרישת הכיסוי נכשלה."
    }
};

const I18N_DIRECTIONS = {
    en: "ltr",
    ru: "ltr",
    he: "rtl"
};

function getSavedLanguage() {
    const saved = localStorage.getItem("scheduleAppLanguage");
    if (saved && I18N_TRANSLATIONS[saved]) {
        return saved;
    }

    const browserLang = (navigator.language || "").toLowerCase();

    if (browserLang.startsWith("he")) return "he";
    if (browserLang.startsWith("ru")) return "ru";
    return "en";
}

function setLanguage(lang) {
    if (!I18N_TRANSLATIONS[lang]) {
        lang = "en";
    }

    localStorage.setItem("scheduleAppLanguage", lang);

    const direction = I18N_DIRECTIONS[lang] || "ltr";
    const html = document.documentElement;
    const body = document.body;

    html.setAttribute("lang", lang);
    html.setAttribute("dir", direction);

    body.classList.remove("rtl", "ltr");
    body.classList.add(direction);

    applyTranslations(lang);
    updateLanguageButtons(lang);

    document.dispatchEvent(new CustomEvent("app-language-changed", {
        detail: { language: lang, direction }
    }));
}

function translate(key, lang = null) {
    const currentLang = lang || localStorage.getItem("scheduleAppLanguage") || "en";
    const dictionary = I18N_TRANSLATIONS[currentLang] || I18N_TRANSLATIONS.en;
    return dictionary[key] ?? key;
}

function applyTranslations(lang) {
    const dictionary = I18N_TRANSLATIONS[lang] || I18N_TRANSLATIONS.en;

    document.querySelectorAll("[data-i18n]").forEach(element => {
        const key = element.dataset.i18n;
        element.textContent = dictionary[key] ?? key;
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
        const key = element.dataset.i18nPlaceholder;
        element.setAttribute("placeholder", dictionary[key] ?? key);
    });

    document.querySelectorAll("[data-i18n-title]").forEach(element => {
        const key = element.dataset.i18nTitle;
        element.setAttribute("title", dictionary[key] ?? key);
    });
}

function updateLanguageButtons(activeLang) {
    document.querySelectorAll(".lang-btn").forEach(button => {
        const isActive = button.dataset.lang === activeLang;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
}

function bindLanguageSwitcher() {
    document.querySelectorAll(".lang-btn").forEach(button => {
        button.addEventListener("click", () => {
            const lang = button.dataset.lang;
            setLanguage(lang);
        });
    });
}

function ensureConfirmModal() {
    let modal = document.getElementById("app-confirm-modal");
    if (modal) return modal;

    modal = document.createElement("div");
    modal.id = "app-confirm-modal";
    modal.className = "app-modal-overlay";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
        <div class="app-modal" role="dialog" aria-modal="true" aria-labelledby="app-confirm-title">
            <div class="app-modal-header">
                <h2 id="app-confirm-title" class="app-modal-title"></h2>
                <button class="app-modal-close" type="button" data-confirm-result="false" aria-label="Close">×</button>
            </div>
            <div class="app-modal-body" id="app-confirm-message"></div>
            <div class="app-modal-actions">
                <button class="btn btn-secondary" type="button" data-confirm-result="false"></button>
                <button class="btn btn-danger" type="button" data-confirm-result="true"></button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    return modal;
}

function appConfirm(message, options = {}) {
    const modal = ensureConfirmModal();
    const title = modal.querySelector("#app-confirm-title");
    const messageBox = modal.querySelector("#app-confirm-message");
    const cancelButton = modal.querySelector('[data-confirm-result="false"].btn');
    const confirmButton = modal.querySelector('[data-confirm-result="true"]');

    title.textContent = options.title || translate("common_confirm");
    if (options.html) {
        messageBox.innerHTML = message || "";
    } else {
        messageBox.textContent = message || "";
    }
    cancelButton.textContent = options.cancelText || translate("common_cancel");
    confirmButton.textContent = options.confirmText || translate("common_delete");

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    confirmButton.focus();

    return new Promise(resolve => {
        const finish = result => {
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
            modal.removeEventListener("click", onModalClick);
            document.removeEventListener("keydown", onKeyDown);
            resolve(result);
        };

        const onModalClick = event => {
            const resultButton = event.target.closest("[data-confirm-result]");
            if (resultButton) {
                finish(resultButton.dataset.confirmResult === "true");
                return;
            }
            if (event.target === modal) {
                finish(false);
            }
        };

        const onKeyDown = event => {
            if (event.key === "Escape") {
                finish(false);
            }
        };

        modal.addEventListener("click", onModalClick);
        document.addEventListener("keydown", onKeyDown);
    });
}

function renderPageMessage(target = "message-box", text = "", type = "info", options = {}) {
    const box = typeof target === "string" ? document.getElementById(target) : target;
    if (!box) return;
    const message = options.html ? String(text || "") : escapeHtml(text);
    box.innerHTML = `<div class="page-message ${type || "info"}">${message}</div>`;
}

function renderEmptyState(options = {}) {
    const title = escapeHtml(options.title || "");
    const text = escapeHtml(options.text || "");
    const actionHtml = options.actionHtml || "";

    return `
        <div class="empty-state">
            ${title ? `<p class="empty-state-title">${title}</p>` : ""}
            ${text ? `<p class="empty-state-text">${text}</p>` : ""}
            ${actionHtml ? `<div class="empty-state-actions">${actionHtml}</div>` : ""}
        </div>
    `;
}

window.appConfirm = appConfirm;
window.renderPageMessage = renderPageMessage;
window.renderEmptyState = renderEmptyState;

document.addEventListener("DOMContentLoaded", () => {
    bindLanguageSwitcher();
    setLanguage(getSavedLanguage());
    bindSidebarToggle();
    applySidebarState(getSavedSidebarState());
});

function getSavedSidebarState() {
    return localStorage.getItem("scheduleAppSidebar") || "expanded";
}

function applySidebarState(state) {
    document.body.classList.remove("sidebar-collapsed");

    if (window.innerWidth <= 920) {
        document.body.classList.remove("mobile-sidebar-hidden");

        if (state === "hidden") {
            document.body.classList.add("mobile-sidebar-hidden");
        }
        return;
    }

    if (state === "collapsed") {
        document.body.classList.add("sidebar-collapsed");
    }
}

function toggleSidebar() {
    if (window.innerWidth <= 920) {
        const hiddenNow = document.body.classList.contains("mobile-sidebar-hidden");
        const nextState = hiddenNow ? "expanded" : "hidden";
        localStorage.setItem("scheduleAppSidebar", nextState);
        applySidebarState(nextState);
        return;
    }

    const collapsedNow = document.body.classList.contains("sidebar-collapsed");
    const nextState = collapsedNow ? "expanded" : "collapsed";
    localStorage.setItem("scheduleAppSidebar", nextState);
    applySidebarState(nextState);
}

function bindSidebarToggle() {
    const button = document.getElementById("sidebar-toggle");
    if (!button) return;

    button.addEventListener("click", toggleSidebar);
}

window.addEventListener("resize", () => {
    applySidebarState(getSavedSidebarState());
});

