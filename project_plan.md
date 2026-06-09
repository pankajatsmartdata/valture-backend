Valture Detail summary:
Valture operates as a comprehensive, multi-tenant marketing simulation platform. New users initiate their journey by signing up and verifying their email address, followed by logging into the secure system. Upon entry, they can create a new workspace or select an existing one, then proceed to establish or choose a specific project within that workspace. The platform enables project administrators to invite new members and assign granular roles (e.g., Admin, Analyst, Viewer) to control access and permissions effectively.
Authorized members, based on their assigned roles, can upload diverse datasets directly via CSV/Excel files or integrate seamlessly with external CRM APIs. The system then triggers an automated data pipeline adhering to the Medallion architecture: the 'Bronze' layer ingests raw data without modification; the 'Silver' layer performs essential data quality checks and PII (Personally Identifiable Information) clearance for compliance; finally, the 'Gold' layer executes sophisticated feature engineering to prepare the dataset for modeling. Crucially, the system maintains dataset versioning, allowing users to rollback to previous states if necessary.
From the refined 'Gold' dataset, the platform facilitates persona profiling. This involves applying unsupervised clustering algorithms (e.g., K-Means, DBSCAN) where the optimal number of clusters can be determined automatically using metrics like the Silhouette Score or set manually according to user-defined business rules.
Simultaneously, the 'Gold' dataset is fed into the machine learning training pipeline. Multiple models, including XGBoost, LightGBM, and Random Forest, are trained to predict customer churn probability. A robust simulation engine is engineered to leverage these trained models. It allows users to input various marketing budget allocations and timeframes, simulating potential outcomes across different channels (e.g., SMS, Email). The engine then calculates and presents projected Return on Investment (ROI), enabling data-driven decision-making for marketing strategies and resource allocation.

Valture Platform Flow:
New User → Signs Up → Email Verification → Login
Logged User → Select/Create Workspace → Select/Create Project → Invite Members & Assign Roles (Admin/Analyst/Viewer)
Authorized Member (based on role) → Upload Dataset (CSV/Excel/CRM API Integration)
Dataset Upload → Triggers Automated Pipeline → Medallion Architecture Execution:
Raw Data → Bronze Layer (Ingestion)
Bronze Output → Silver Layer (Data Quality + PII Clearance)
Silver Output → Gold Layer (Feature Engineering)
Gold Layer → Dataset Versioning & Rollback Capability
Gold Dataset → Persona Profiling Engine → Clustering Algorithms → Optimal Cluster Selection (Silhouette Score / Manual Rule Definition)
Gold Dataset → ML Training Pipeline → Model Training (XGBoost → LightGBM → Random Forest)
Trained Models + Business Parameters → Simulation Engine Activation → Input Budget/Time/Channels (SMS ← Email ← Others) → Output ROI Projections
Result → Data-Driven Marketing Strategy Decisions


Below are the Progress Planning or project in phases.
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

Phase 2: Tenant Schema & Workspace Initialization
    - Schema Template Engine: Develop the system responsible for creating new database schemas based on predefined templates. This template includes tables relevant to the business logic (datasets, models, simulations, etc.) but not the global User table.
    - Workspace Creation Process:
        - Upon successful organization creation (from Phase 1), trigger the schema creation using the template.
        - Assign the initiating user as an administrator within this newly created schema/workspace.
        - Establish the initial medallion architecture structure (bronze, silver, gold) within the new schema if needed from the start.
    - Schema Mapping: Maintain a mapping table (likely in the central schema) linking Users/Workspaces to their respective database schemas.
    - Tenant Context Middleware: Implement middleware to identify the requesting user and their active organization/workspace from the JWT token or request headers, and dynamically connect subsequent database queries to the correct tenant schema.

Phase 3: Workspace & Workspace Management
    - Workspace CRUD: APIs to create, read, update, and delete central Workspace records (linking to schemas).
    - Workspace Context: APIs for users to view accessible workspaces and switch active schema context.
    - Schema RBAC Setup: Initialize role/permission tables within new tenant schemas; assign the creator as admin. Basic role assignment API for admins.
    - User Access Mapping: Maintain central tables mapping global user_id to organization_id and schema_name.
    - Invitation System: Generate and accept invitations to add global users to an organization/schema mapping.
    - API Key Management: Generate, store (in tenant schema), and authenticate API keys scoped to the active workspace and user permissions.

