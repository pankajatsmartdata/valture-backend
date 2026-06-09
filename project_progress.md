This file includes the progress of the feature those were completed and tested successfully.
In case you want to get the more information from the particular phase instead of summary bullet points, you better look inside the file of app/directory with the same name of the directory but with the markdown extension (e.g: Users.md inside the directory 'api/users/Users.md')

Phase 1: Global Authentication & Core User Management
    - Global User Model: Design and implement the User model in a central/default schema (e.g., public). This table holds common user fields like email, username, password hash, basic profile, etc.
    - Authentication System:
        - Signup API: Handles user registration, creates a record in the global User table. Initiates the creation of the user's first organization/workspace (or links them to an invited one).
        - Login API: Authenticates against the global User table, generates JWT tokens containing user ID and potentially default organization context.
        - Account Verification: Email verification linked to the global User record.
        - Password Management: Forgot/reset password flows operating on the global User table.
    - Profile Management: Update operations on the global user profile.
    - Workspace Management:
        Create Workspace API: Allows a user to create a new organization. This triggers the process in Phase 2.
        Join Workspace: Mechanism for users to join existing Workspaces (e.g., via invitations linked to their global user email).
