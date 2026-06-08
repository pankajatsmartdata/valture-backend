# User Authentication API Documentation

## Overview
This document provides a reference for the user authentication system in the Valture backend. It covers the data model, token handling, and all related API endpoints, including request and response payloads.

---

## Data Model
**User** (`api/users/models.py`)
- `email` (unique, primary identifier)
- `first_name`, `last_name`
- `is_verified` – email verification status
- `is_active`, `is_staff`, `is_superuser`
- `date_joined`
- Inherits from `AbstractBaseUser` and `PermissionsMixin`
- Password stored as a hash via `set_password`

**Workspace Mapping** (`api/workspaces/models.py` – referenced in serializers) – maps a user to a workspace with a `role`.

---

## Token Generation
- JWTs are issued via **LoginView** (`TokenObtainPairView`) using `CustomTokenObtainPairSerializer`.
- Tokens embed:
  - `workspace_id` – the active workspace for the user.
  - `role` – the user's role within that workspace.
- The same fields are added to the **refresh token**.

---

## API Endpoints
### 1. **Signup** – `POST /api/auth/signup/`
**Request Body** (JSON)
```json
{
  "email": "user@example.com",
  "password": "StrongPassword!",
  "first_name": "John",
  "last_name": "Doe",
  "workspace_name": "John's Workspace"  // optional
}
```
**Response** (201 Created)
```json
{
  "message": "User registered successfully. Please check your email for the verification link."
}
```
- Creates a `User`.
- If there are pending `WorkspaceInvitation`s for the email, the user is added to those workspaces.
- Otherwise a new workspace is created (default name derived from first name or email).
- An email verification link is generated using `FRONTEND_URL` and sent via `send_mail` (logged to console in dev).

---

### 2. **Email Verification** – `GET /api/auth/verify/?token=<token>`
**Query Parameter**: `token` – signed email token (valid 24 h).
**Response** (200 OK)
```json
{"message": "Email verified successfully."}
```
- Marks `User.is_verified` as `True`.

---

### 3. **Login** – `POST /api/auth/login/`
Uses `CustomTokenObtainPairSerializer` (extends SimpleJWT). Payload:
```json
{ "email": "user@example.com", "password": "Secret" }
```
**Response** (200 OK)
```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>",
  "active_workspace": {"id": "<ws_id>", "name": "<ws_name>", "slug": "<ws_slug>", "role": "owner"},
  "workspaces": [
    {"id": "<ws_id>", "name": "<ws_name>", "slug": "<ws_slug>", "role": "owner"}
  ]
}
```
- Tokens contain `workspace_id` and `role` claims.

---

### 4. **Switch Workspace** – `POST /api/auth/switch-workspace/`
**Request Body**
```json
{ "workspace_id": "<workspace_uuid>" }
```
**Response** (200 OK) – Same shape as login response but with a new access token for the selected workspace.
- Validates that the user is a member of the requested workspace (`UserWorkspaceMapping`).
- Generates fresh JWTs with the new `workspace_id` and role.

---

### 5. **User Profile** – `GET /api/auth/profile/`
**Response** (200 OK)
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_verified": true
}
```
**Patch** (`PATCH /api/auth/profile/`) – Partial update of `first_name`, `last_name`, etc.

---

### 6. **Password Reset Request** – `POST /api/auth/password-reset/`
**Request Body**
```json
{ "email": "user@example.com" }
```
**Response** (200 OK)
```json
{"message": "If the email exists, a password reset link has been sent."}
```
- Generates a signed token (valid 1 h) and sends a reset link using `FRONTEND_URL`.

---

### 7. **Password Reset Confirm** – `POST /api/auth/password-reset-confirm/`
**Request Body**
```json
{ "token": "<reset_token>", "password": "NewStrongPassword!" }
```
**Response** (200 OK)
```json
{"message": "Password reset successfully."}
```
- Validates token age (1 h) and password strength before updating the user's password.

---

## Serializer Overview
- **UserSerializer** – fields: `id`, `email`, `first_name`, `last_name`, `is_verified` (read‑only).
- **UserSignupSerializer** – creates user, optional `workspace_name`, validates password.
- **CustomTokenObtainPairSerializer** – adds `workspace_id`, `role`, `active_workspace`, and `workspaces` to the token response.

---

## Environment Variable
All URLs now use `FRONTEND_URL` from `.env` (default `http://localhost:8000`).

---

*End of documentation*