I am going to build the marketing simulation project backend APIs in python DRF + FastAPI. Where DRF will be in the main role play for the communication between the microservices and handling the database migration too. The data base we have picked is PostgreSQL. 

## Application flow overview:
We are building the SAAS platform, where we are providing the multi-tenant schema based separation for the each workspace. To derive the Application flow, we will ask the login creds or signup(new user). After login or signup(verify the email), give the option to join the workspace by providing the workspace id or can create the new workspace if needed.
