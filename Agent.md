# Multi-Tenant Schema Isolation — Raw SQL Approach

Convert from the current "Phase 1 single-schema simulation" to true per-workspace PostgreSQL schema isolation using raw SQL templates.

## Target Architecture

```
public schema (Django-managed)            per-workspace schema e.g. tenant_johns_ws (raw SQL)
├── users                                 ├── workspace_members
├── workspaces                            ├── workspace_invitations
├── user_workspace_mappings               └── (future: projects, etc.)
└── (django internal tables)
```

---

## Open Questions

> [!IMPORTANT]
> **Invitation token lookup**: When a user clicks a join link, we need to find the invitation. Since invitations will live inside workspace schemas, the join URL needs to include `workspace_id` so we know which schema to search. The URL will become:
> `/api/workspaces/<workspace_id>/join/?token=<token>`
> Is this acceptable?

> [!IMPORTANT]
> **Signup auto-join**: Currently, when a user signs up, we search all `WorkspaceInvitation` records for their email and auto-join them. With per-schema invitations, we'd need to search across all schemas. Two options:
> 1. **Keep a lightweight `pending_invitations` table in public schema** — just `(email, workspace_id, token)` for cross-workspace lookup. Full details stay in the workspace schema.
> 2. **Remove auto-join from signup** — user signs up, then manually clicks the invitation link to join. Simpler architecture.
>
> Which do you prefer?

---

## Proposed Changes

### 1. Schema Manager (NEW)

#### [NEW] [schema_manager.py](file:///home/pankajj/Desktop/valture/valture-backend/api/workspaces/schema_manager.py)

A utility module for schema lifecycle operations:

- **`create_workspace_schema(schema_name)`** — Runs raw SQL:
  1. `CREATE SCHEMA IF NOT EXISTS <schema_name>;`
  2. Creates `workspace_members` table inside the schema (with FK to `public.users`)
  3. Creates `workspace_invitations` table inside the schema
  4. Adds appropriate indexes and constraints

- **`drop_workspace_schema(schema_name)`** — Runs `DROP SCHEMA <schema_name> CASCADE;` for cleanup.

- **`set_search_path(schema_name)`** — Helper to run `SET search_path TO <schema_name>, public;` on the current DB connection.

- **`reset_search_path()`** — Resets to `SET search_path TO public;`.

Raw SQL template for tenant tables:
```sql
CREATE TABLE IF NOT EXISTS {schema}.workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    email VARCHAR(254) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id),
    UNIQUE(email)
);

CREATE TABLE IF NOT EXISTS {schema}.workspace_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(254) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    token UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(email)  -- one pending invite per email per workspace
);
```

---

### 2. Workspace Schema Middleware (NEW)

#### [NEW] [middleware.py](file:///home/pankajj/Desktop/valture/valture-backend/api/workspaces/middleware.py)

A Django middleware that sets the PostgreSQL `search_path` per request:

1. Runs **after** `AuthenticationMiddleware` (JWT is decoded at that point).
2. Reads `workspace_id` from the JWT token payload.
3. Looks up `Workspace.schema_name` from the database (with caching).
4. Executes `SET search_path TO <schema_name>, public;` on the current connection.
5. After the response, resets to `SET search_path TO public;`.
6. **Skips** for unauthenticated routes (signup, login, verify, password-reset).

---

### 3. Model Changes

#### [MODIFY] [models.py](file:///home/pankajj/Desktop/valture/valture-backend/api/workspace_tenant/models.py)

- Set `managed = False` on both `WorkspaceMember` and `WorkspaceInvitation` (tables created by raw SQL, not Django migrations).
- **Remove** the `workspace` FK from both models (schema isolation replaces it).
- Adjust `unique_together` constraints (no longer need `workspace` in the constraint since each schema is one workspace).

```python
class WorkspaceMember(models.Model):
    # workspace FK REMOVED — schema isolation handles this
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, ...)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'workspace_members'
```

Same pattern for `WorkspaceInvitation`.

---

### 4. Update Signup Flow

#### [MODIFY] [serializers.py](file:///home/pankajj/Desktop/valture/valture-backend/api/users/serializers.py)

- After `Workspace.objects.create(...)`, call `create_workspace_schema(schema_name)` to provision the actual PostgreSQL schema + tables.
- For the pending-invitation auto-join: update based on decision from Open Questions above.
- When creating `WorkspaceMember` during signup, first set `search_path` to the workspace schema.

---

### 5. Update Tenant Views

#### [MODIFY] [views.py](file:///home/pankajj/Desktop/valture/valture-backend/api/workspace_tenant/views.py)

- **`WorkspaceMemberListView`**: Remove `.filter(workspace_id=...)`. The middleware already sets `search_path` to the correct schema, so `WorkspaceMember.objects.all()` returns only that workspace's members.
- **`WorkspaceInviteView`**: Set `search_path` to target workspace schema before creating invitation. Remove `workspace=workspace` from serializer context/creation.
- **`WorkspaceJoinView`**: Look up workspace from URL `workspace_id`, set `search_path`, then find the invitation by token within that schema.

#### [MODIFY] [serializers.py](file:///home/pankajj/Desktop/valture/valture-backend/api/workspace_tenant/serializers.py)

- Remove `workspace` from `WorkspaceMemberSerializer` fields.
- Remove `workspace`-based filter queries from `WorkspaceInvitationSerializer.validate()` — since we're already in the correct schema, just filter by email.
- Remove `workspace=workspace` from `create()`.

#### [MODIFY] [urls.py](file:///home/pankajj/Desktop/valture/valture-backend/api/workspace_tenant/urls.py)

- Update join URL to include `workspace_id`: `workspaces/<uuid:workspace_id>/join/`

---

### 6. Settings Update

#### [MODIFY] [settings.py](file:///home/pankajj/Desktop/valture/valture-backend/valture/settings.py)

- Add the new middleware to `MIDDLEWARE` list (after `AuthenticationMiddleware`).
- Remove duplicate `EMAIL_BACKEND` at bottom of file (line 189 overrides the SMTP config at line 59).

---

### 7. Migration Strategy

#### [NEW] management command `provision_schemas`

A one-time management command to:
1. Loop through all existing `Workspace` records.
2. For each, call `create_workspace_schema(schema_name)`.
3. Migrate existing `workspace_members` and `workspace_invitations` rows from public schema into the correct workspace schema.
4. Generate a Django migration to remove the old public-schema tables (or set `managed = False`).

---

## File Summary

| File | Action | Purpose |
|------|--------|---------|
| `api/workspaces/schema_manager.py` | NEW | Raw SQL schema creation/deletion |
| `api/workspaces/middleware.py` | NEW | Per-request `search_path` switching |
| `api/workspace_tenant/models.py` | MODIFY | `managed=False`, remove `workspace` FK |
| `api/workspace_tenant/views.py` | MODIFY | Remove workspace FK filtering, use schema context |
| `api/workspace_tenant/serializers.py` | MODIFY | Remove workspace from fields/creation |
| `api/workspace_tenant/urls.py` | MODIFY | Add workspace_id to join URL |
| `api/users/serializers.py` | MODIFY | Call `create_workspace_schema()` on signup |
| `valture/settings.py` | MODIFY | Add middleware, fix duplicate EMAIL_BACKEND |
| management command | NEW | One-time data migration |

---

## Verification Plan

### Automated Tests
- Create a test that signs up a user → verifies a PostgreSQL schema was created.
- Create a test that invites a user → verifies the invitation exists only in the correct schema.
- Create a test that switches workspace → verifies queries hit the correct schema.

### Manual Verification
```bash
# After signup, check the schema exists in PostgreSQL:
psql -c "\dn"  # list all schemas

# Check tables inside the schema:
psql -c "\dt tenant_johns_workspace.*"

# Verify data isolation:
psql -c "SET search_path TO tenant_johns_workspace; SELECT * FROM workspace_members;"
```
