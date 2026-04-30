-- Schedule App 0.14.x beta PostgreSQL baseline.
-- Apply to an empty Cloud SQL PostgreSQL database before enabling the PostgreSQL data layer.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    id BIGSERIAL PRIMARY KEY,
    from_version INTEGER NOT NULL,
    to_version INTEGER NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organizations (
    id BIGSERIAL PRIMARY KEY,
    public_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO organizations (id, public_id, name, status)
VALUES (1, 'local-default', 'Local Organization', 'active')
ON CONFLICT (id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('organizations', 'id'), (SELECT MAX(id) FROM organizations));

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT,
    status TEXT NOT NULL DEFAULT 'invited' CHECK (status IN ('invited', 'active', 'disabled')),
    email_verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS employees (
    id BIGSERIAL PRIMARY KEY,
    id_card TEXT,
    full_name TEXT NOT NULL,
    sex TEXT NOT NULL CHECK (sex IN ('male', 'female')),
    min_shifts_per_week INTEGER NOT NULL,
    target_shifts_per_week INTEGER NOT NULL DEFAULT 0,
    max_shifts_per_week INTEGER NOT NULL,
    can_work_night INTEGER NOT NULL,
    can_work_weekends INTEGER NOT NULL,
    can_work_evenings_after_night INTEGER NOT NULL,
    can_work_mornings_and_evenings INTEGER NOT NULL,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('emp_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (public_id)
);

ALTER TABLE employees ADD COLUMN IF NOT EXISTS id_card TEXT;

CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#eff6ff',
    requires_continuous_coverage INTEGER NOT NULL DEFAULT 0,
    minimum_staff_presence INTEGER NOT NULL DEFAULT 0,
    max_consecutive_nights INTEGER,
    emergency_max_consecutive_nights INTEGER,
    max_consecutive_split_days INTEGER,
    emergency_max_consecutive_split_days INTEGER,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('pos_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (public_id)
);

CREATE TABLE IF NOT EXISTS organization_memberships (
    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'scheduler', 'employee', 'manager', 'read_only')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('invited', 'active', 'disabled')),
    employee_id BIGINT REFERENCES employees(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE IF NOT EXISTS organization_invitations (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    employee_id BIGINT REFERENCES employees(id) ON DELETE SET NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'scheduler', 'employee', 'manager', 'read_only')),
    token_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'revoked')),
    expires_at TEXT NOT NULL,
    accepted_at TEXT,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_audit_events (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT REFERENCES organizations(id) ON DELETE SET NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    actor_ip TEXT,
    user_agent TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS auth_password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_email_verification_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS desktop_sync_outbox (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_public_id TEXT,
    operation TEXT NOT NULL CHECK (operation IN ('upsert', 'delete', 'replace')),
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'syncing', 'synced', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    next_attempt_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS employee_positions (
    employee_id BIGINT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    position_id BIGINT NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    is_primary INTEGER NOT NULL DEFAULT 0,
    priority_score INTEGER NOT NULL DEFAULT 50,
    is_fallback_only INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (employee_id, position_id)
);

CREATE TABLE IF NOT EXISTS shift_templates (
    id BIGSERIAL PRIMARY KEY,
    position_id BIGINT REFERENCES positions(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN ('morning', 'evening', 'night')),
    name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_overnight INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_split_only INTEGER NOT NULL DEFAULT 0,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('tpl_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (position_id, name),
    UNIQUE (public_id)
);

CREATE TABLE IF NOT EXISTS schedule_entries (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    position_id BIGINT NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    shift_template_id BIGINT NOT NULL REFERENCES shift_templates(id) ON DELETE RESTRICT,
    no_show INTEGER NOT NULL DEFAULT 0,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('sch_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (public_id)
);

CREATE TABLE IF NOT EXISTS shift_requirements (
    id BIGSERIAL PRIMARY KEY,
    position_id BIGINT NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    shift_category TEXT NOT NULL CHECK (shift_category IN ('morning', 'evening', 'night')),
    required_total INTEGER NOT NULL,
    required_female_min INTEGER NOT NULL,
    required_male_min INTEGER NOT NULL DEFAULT 0,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('shr_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (position_id, shift_category),
    UNIQUE (public_id)
);

CREATE TABLE IF NOT EXISTS employee_preferences (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL UNIQUE REFERENCES employees(id) ON DELETE CASCADE,
    allow_morning INTEGER NOT NULL,
    allow_evening INTEGER NOT NULL,
    allow_night INTEGER NOT NULL,
    allow_morning_evening_combo INTEGER NOT NULL,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('prf_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (public_id)
);

CREATE TABLE IF NOT EXISTS employee_week_preferences (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    week_start_date TEXT NOT NULL,
    preference_date TEXT NOT NULL,
    preference_type TEXT NOT NULL,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('wpr_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (employee_id, preference_date),
    UNIQUE (public_id)
);

CREATE TABLE IF NOT EXISTS employee_day_statuses (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    status_type TEXT NOT NULL CHECK (status_type IN ('sick', 'day_off')),
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('dst_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (employee_id, date),
    UNIQUE (public_id)
);

CREATE TABLE IF NOT EXISTS coverage_requirements (
    id BIGSERIAL PRIMARY KEY,
    position_id BIGINT NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    required_total INTEGER NOT NULL,
    required_female_min INTEGER NOT NULL DEFAULT 0,
    required_male_min INTEGER NOT NULL DEFAULT 0,
    is_overnight INTEGER NOT NULL DEFAULT 0,
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    public_id TEXT NOT NULL DEFAULT ('cov_' || lower(encode(gen_random_bytes(16), 'hex'))),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (public_id)
);

CREATE TABLE IF NOT EXISTS app_settings (
    organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id) ON DELETE CASCADE,
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO app_settings (organization_id, key, value)
VALUES
    (1, 'min_rest_minutes_between_morning_and_evening', '0'),
    (1, 'min_rest_minutes_after_night_before_evening', '480'),
    (1, 'schedule_coverage_display_mode', 'interval'),
    (1, 'schedule_morning_color', '#ecfeff'),
    (1, 'schedule_evening_color', '#fff7ed'),
    (1, 'schedule_night_color', '#eef2ff'),
    (1, 'schedule_status_color', '#f5f3ff'),
    (1, 'max_work_days_per_week', '6'),
    (1, 'max_consecutive_nights', '2'),
    (1, 'emergency_max_consecutive_nights', '3'),
    (1, 'max_consecutive_split_days', '2'),
    (1, 'emergency_max_consecutive_split_days', '3'),
    (1, 'allow_multiple_positions_per_day', '0'),
    (1, 'after_night_evening_penalty', '1200'),
    (1, 'consecutive_night_penalty', '500'),
    (1, 'consecutive_split_penalty', '450'),
    (1, 'coverage_shortage_gain_weight', '100'),
    (1, 'coverage_overage_penalty_weight', '25'),
    (1, 'target_gender_bonus_weight', '250'),
    (1, 'wrong_gender_penalty_weight', '120'),
    (1, 'balance_missing_min_weight', '300'),
    (1, 'balance_target_distance_weight', '70'),
    (1, 'balance_over_target_weight', '80'),
    (1, 'balance_over_max_weight', '10000'),
    (1, 'balance_worked_day_weight', '15'),
    (1, 'balance_night_weight', '60'),
    (1, 'balance_split_weight', '55'),
    (1, 'balance_consecutive_night_weight', '120'),
    (1, 'balance_consecutive_split_weight', '100'),
    (1, 'balance_excess_night_weight', '2000'),
    (1, 'balance_excess_split_weight', '1800')
ON CONFLICT (key) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON organization_memberships (user_id, organization_id);
CREATE INDEX IF NOT EXISTS idx_invitations_org_email_status ON organization_invitations (organization_id, email, status);
CREATE INDEX IF NOT EXISTS idx_auth_audit_events_org_created ON auth_audit_events (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_active ON auth_sessions (user_id, expires_at, revoked_at);
CREATE INDEX IF NOT EXISTS idx_auth_password_reset_tokens_user ON auth_password_reset_tokens (user_id, expires_at, used_at);
CREATE INDEX IF NOT EXISTS idx_auth_email_verification_tokens_user ON auth_email_verification_tokens (user_id, expires_at, used_at);
CREATE INDEX IF NOT EXISTS idx_desktop_sync_outbox_pending ON desktop_sync_outbox (status, next_attempt_at, created_at);
CREATE INDEX IF NOT EXISTS idx_employees_org ON employees (organization_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_org_id_card ON employees (organization_id, id_card) WHERE id_card IS NOT NULL AND id_card <> '';
CREATE INDEX IF NOT EXISTS idx_positions_org ON positions (organization_id, id);
CREATE INDEX IF NOT EXISTS idx_shift_templates_position_active ON shift_templates (position_id, is_active, category, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_shift_templates_org ON shift_templates (organization_id, position_id);
CREATE INDEX IF NOT EXISTS idx_schedule_entries_employee_date ON schedule_entries (employee_id, date);
CREATE INDEX IF NOT EXISTS idx_schedule_entries_position_date ON schedule_entries (position_id, date);
CREATE INDEX IF NOT EXISTS idx_schedule_entries_org_date ON schedule_entries (organization_id, date);
CREATE INDEX IF NOT EXISTS idx_employee_positions_position_employee ON employee_positions (position_id, employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_day_statuses_employee_date ON employee_day_statuses (employee_id, date);
CREATE INDEX IF NOT EXISTS idx_employee_week_preferences_employee_week ON employee_week_preferences (employee_id, week_start_date, preference_date);
CREATE INDEX IF NOT EXISTS idx_employee_week_preferences_org_week ON employee_week_preferences (organization_id, week_start_date, preference_date);
CREATE INDEX IF NOT EXISTS idx_coverage_requirements_position ON coverage_requirements (position_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_coverage_requirements_org_position ON coverage_requirements (organization_id, position_id);
CREATE INDEX IF NOT EXISTS idx_app_settings_organization ON app_settings (organization_id, key);

INSERT INTO schema_metadata (key, value)
VALUES ('schema_version', '16')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
