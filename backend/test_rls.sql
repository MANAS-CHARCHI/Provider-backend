-- 1. Enable RLS on your data table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 2. Force RLS so even the table owner is restricted (recommended for security)
ALTER TABLE users FORCE ROW LEVEL SECURITY;

-- 3. Create a policy: Only allow access if user_id matches the session variable
CREATE POLICY user_isolation_policy ON users FOR ALL USING (
    id = current_setting('app.user_id')::uuid
);

--IMP: Tell the postgres force security policy every for the owner as well
ALTER TABLE users FORCE ROW LEVEL SECURITY;

ALTER TABLE users DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_isolation_policy ON users;

SELECT rolname, rolsuper FROM pg_roles WHERE rolname = CURRENT_USER;

SELECT rolname, rolsuper FROM pg_roles;

GRANT USAGE ON SCHEMA public TO manas;

GRANT ALL PRIVILEGES ON users TO manas;

GRANT ALL PRIVILEGES ON TABLE activations TO manas;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO manas;

-- 3. If you have other tables (like TokenBlacklist or Invitations), grant them too
GRANT ALL PRIVILEGES ON TABLE token_blacklist TO manas;

GRANT ALL PRIVILEGES ON TABLE invitations TO manas;

ALTER ROLE manas NOSUPERUSER NOBYPASSRLS;
-- create a new role
CREATE ROLE manas WITH LOGIN PASSWORD 'manas';

-- 1. Reset permissions for your app user (manas)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO manas;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO manas;

-- 2. Enable RLS and Force it (crucial for 2026 security)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

ALTER TABLE users FORCE ROW LEVEL SECURITY;

-- 3. Allow anyone to REGISTER (Insert only)
-- No one can SEE the table during this, they can only add to it.
DROP POLICY IF EXISTS registration_policy ON users;

CREATE POLICY registration_policy ON users FOR INSERT
WITH
    CHECK (true);

-- 4. Allow LOGIN lookup (Select by ID or Email)
-- This only works if the session variable is NOT set (during login)
-- or if the ID matches the session variable (after login)
DROP POLICY IF EXISTS user_isolation_policy ON users;

CREATE POLICY user_isolation_policy ON users FOR
SELECT USING (
        -- Case A: User is logged in (ID must match token)
        id = current_setting('app.user_id', true)::uuid
        OR
        -- Case B: During Login/Registration lookup 
        -- (Allow lookup only if the app hasn't set a user context yet)
        current_setting('app.user_id', true) = ''
    );

-- 5. Allow users to UPDATE only their own data
CREATE POLICY user_update_policy ON users
FOR UPDATE
    USING (
        id = current_setting('app.user_id', true)::uuid
    );
-- 6. Policy: Allow Login Lookups (Select by email)
-- This is a 'Public' lookup policy
CREATE POLICY login_lookup_policy ON users FOR SELECT USING (true);

-- 7. Policy: Data Isolation (The actual RLS)
-- This overrides the 'true' using RESTRICTIVE logic if needed,
-- but for simplicity, we use one FOR ALL policy:
DROP POLICY IF EXISTS user_isolation_policy ON users;

CREATE POLICY user_isolation_policy ON users FOR ALL TO manas USING (
    id = current_setting('app.user_id', true)::uuid
);