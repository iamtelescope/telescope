# Authentication & Authorization

## Authentication

Telescope utilizes [Django's](https://www.djangoproject.com/) default authentication system.
For GitHub authentication, it uses the [django-allauth](https://docs.allauth.org/en/latest/) package.

The basic authentication flow is as follows:

* The user provides credentials (username and password) or logs in via a social account (e.g., GitHub).
* The backend verifies the credentials and stores the session object in the database.
* For each request, the session is validated and verified.

## Authorization

Most of actions in telescope are protected via RBAC.

RBAC is an access control model that restricts system access based on user roles. It ensures that users have only the permissions necessary to perform their tasks.

A user or group is assigned one or more roles.
Each role contains a set of permissions.
When a user attempts an action, the system checks if their assigned role includes the required permission.
If the permission is granted, the action proceeds; otherwise, access is denied.

There are two kind of roles in Telescope: **Global role** and **Source role**.
Roles and permissions are currently hardcoded in the code, and users cannot create their own roles.

## Global Roles

Global roles apply to the entire system.
There is only one global role: **Admin**.

### **Admin**
This role grants full access to the system.
It includes the following global permissions:

- `global_create_source`
- `global_read_source`
- `global_edit_source`
- `global_grant_source`
- `global_raw_query_source`
- `global_use_source`
- `global_delete_source`

## Source Roles

Source roles are tied to a specific data source.
Available roles and their permissions:

### **Owner**
Has full control over the source.
Permissions:
- `source_read`
- `source_edit`
- `source_delete`
- `source_use`
- `source_grant`
- `source_raw_query`

### **Editor**
Can read, edit, and delete the source.
Permissions:
- `source_read`
- `source_edit`
- `source_delete`

### **Viewer**
Can only read the source.
Permissions:
- `source_read`

### **User**
Can read and use the source.
Permissions:
- `source_read`
- `source_use`

### **Raw Query User**
Can read, use, and execute RAW queries on the source.
Permissions:
- `source_read`
- `source_use`
- `source_raw_query`
