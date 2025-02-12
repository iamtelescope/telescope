# Development environment setup for Telescope

## Architecture Overview

Telescope has a straightforward architecture, consisting of:

- A **backend** written in Python using Django.
- A **frontend** written in JavaScript using Vue.js.

After building and assembling the application, we have a single Django-based app that serves the static files, where the JavaScript application runs

### Role of Django application

Django app serves as the web server responsible for:

- Managing authentication.
- Handling database interactions.
- Handling frontend static files.

Since `index.html` is served through Django app, the user is authenticated before accessing the JavaScript application. This allows Django to enforce authentication at the entry point.

- **Login and logout UI**: Handled by Django.
- **Rest of the UI**: Implemented in Vue.js.
- **UI API**: Django acts as a backend-for-frontend (BFF), serving as an API for the Vue.js frontend using session cookies for authentication. A separate API for automated (robot) access is planned for the future.
- **Database**: Django supports any database compatible with its ORM (e.g., SQLite, PostgreSQL, MySQL).

## Development Workflow

The development process consists of two independent stages:

1. **Backend Development**: Django can be developed separately without running the frontend.
2. **Frontend Development**: Requires the Django development server to be running.

### Prerequisites

To set up the development environment, you need:

- **Python 3.12++**
- **Node.js 20++**

Each OS (Windows, macOS, Linux) has slightly different setup instructions, so refer to their respective official documentation for installation details.

### Setting Up the Environment

#### 1. Setting up Python Environment

1. Create a virtual environment:
   ```sh
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```sh
   cd ./backend
   pip install -r requirements.txt
   ```

#### 2. Setting up Node.js Environment

1. Install dependencies:
   ```sh
   cd ./ui
   npm install
   ```

## Running the Development Servers

### 0. Prepare configuration file
You can start configuring the application using the `dev/config.yaml` file.
For other configuration options, please refer to the [documentation](config.md).

### 1. Running Django Development Server

If this is your first launch, you will need to run the migration step (or if you have made changes to the models).
```sh
cd ./backend
export TELESCOPE_CONFIG_FILE=${HOME}/.telescope/config.yaml
python manage.py migrate
python manage.py runserver
```

### 2. Running Vue.js Development Server

Navigate to the frontend directory and run:

```sh
cd ui
npm run serve
```

### 3. Initial Authentication Step

Before using the frontend, you must log in via the Django server once. This is necessary to obtain a valid session cookie on `localhost`. Without this step, the Vue.js application won't be able to access the API due to missing authentication.

1. Open the Django server in a browser (`http://localhost:8000`).
2. Log in using your credentials.
3. Once logged in, you can start using the Vue.js application (`http://localhost:8080`).

After this initial login, authentication cookies will be set, and you can work seamlessly with the frontend.
