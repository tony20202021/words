#!/usr/bin/env python3
"""
Script to create the project structure for the Language Learning Telegram Bot.
This script will create all necessary directories and empty files.
"""

import os
import sys
from pathlib import Path

def create_directory(path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")

def create_file(path, content=""):
    """Create an empty file if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Created file: {path}")
    else:
        print(f"File already exists: {path}")

def create_python_file(path, module_name=""):
    """Create a Python file with proper imports if it doesn't exist."""
    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    
    # Create basic Python module content
    if module_name:
        content = f'"""\n{module_name}\n"""\n\n'
    else:
        content = '"""\nModule description\n"""\n\n'
    
    create_file(path, content)

def create_init_file(path):
    """Create an __init__.py file."""
    create_file(path, '"""Module initialization."""\n')

def main():
    # Set the root directory
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = "language-learning-bot"
    
    print(f"Creating project structure in: {root_dir}")
    
    # Create root directory
    create_directory(root_dir)
    
    # Create root files
    root_files = [
        "README.md",
        ".gitignore",
        "requirements.txt",
        "environment.yml",
        "docker-compose.yml",
        ".env.example",
        "pyproject.toml",
        "setup.py",
        "project_description.md",
        "directory_structure.md",
    ]
    
    for file in root_files:
        create_file(os.path.join(root_dir, file))
    
    # Create scripts directory and files
    scripts_dir = os.path.join(root_dir, "scripts")
    create_directory(scripts_dir)
    create_python_file(os.path.join(scripts_dir, "init_db.py"), "Script to initialize the database")
    create_python_file(os.path.join(scripts_dir, "seed_data.py"), "Script to seed the database with test data")
    
    # Create docs directory and files
    docs_dir = os.path.join(root_dir, "docs")
    create_directory(docs_dir)
    docs_files = [
        "api.md",
        "bot_commands.md",
        "development.md",
        "project_description.md",
        "directory_structure.md",
    ]
    for file in docs_files:
        create_file(os.path.join(docs_dir, file))
    
    # Frontend structure
    frontend_dir = os.path.join(root_dir, "frontend")
    create_directory(frontend_dir)
    
    # Frontend app directory
    frontend_app_dir = os.path.join(frontend_dir, "app")
    create_directory(frontend_app_dir)
    create_init_file(os.path.join(frontend_app_dir, "__init__.py"))
    create_python_file(os.path.join(frontend_app_dir, "main.py"), "Entry point for the frontend application")
    
    # Frontend bot directory
    bot_dir = os.path.join(frontend_app_dir, "bot")
    create_directory(bot_dir)
    create_init_file(os.path.join(bot_dir, "__init__.py"))
    create_python_file(os.path.join(bot_dir, "bot.py"), "Main bot class")
    
    # Frontend handlers directory
    handlers_dir = os.path.join(bot_dir, "handlers")
    create_directory(handlers_dir)
    create_init_file(os.path.join(handlers_dir, "__init__.py"))
    handlers_files = [
        "admin_handlers.py",
        "user_handlers.py",
        "language_handlers.py",
        "study_handlers.py",
        "hint_handlers.py",
    ]
    for file in handlers_files:
        create_python_file(os.path.join(handlers_dir, file), f"Handlers for {file.split('_')[0]} commands")
    
    # Frontend keyboards directory
    keyboards_dir = os.path.join(bot_dir, "keyboards")
    create_directory(keyboards_dir)
    create_init_file(os.path.join(keyboards_dir, "__init__.py"))
    keyboard_files = [
        "admin_keyboards.py",
        "user_keyboards.py",
        "inline_keyboards.py",
    ]
    for file in keyboard_files:
        create_python_file(os.path.join(keyboards_dir, file), f"Keyboards for {file.split('_')[0]}")
    
    # Frontend states directory
    states_dir = os.path.join(bot_dir, "states")
    create_directory(states_dir)
    create_init_file(os.path.join(states_dir, "__init__.py"))
    states_files = [
        "admin_states.py",
        "user_states.py",
    ]
    for file in states_files:
        create_python_file(os.path.join(states_dir, file), f"States for {file.split('_')[0]}")
    
    # Frontend middleware directory
    middleware_dir = os.path.join(bot_dir, "middleware")
    create_directory(middleware_dir)
    create_init_file(os.path.join(middleware_dir, "__init__.py"))
    create_python_file(os.path.join(middleware_dir, "auth_middleware.py"), "Authentication middleware")
    
    # Frontend api directory
    api_dir = os.path.join(frontend_app_dir, "api")
    create_directory(api_dir)
    create_init_file(os.path.join(api_dir, "__init__.py"))
    create_python_file(os.path.join(api_dir, "client.py"), "API client for the backend")
    
    # Frontend api models directory
    api_models_dir = os.path.join(api_dir, "models")
    create_directory(api_models_dir)
    create_init_file(os.path.join(api_models_dir, "__init__.py"))
    api_model_files = [
        "language.py",
        "user.py",
        "word.py",
    ]
    for file in api_model_files:
        create_python_file(os.path.join(api_models_dir, file), f"Models for {file.split('.')[0]}")
    
    # Frontend utils directory
    utils_dir = os.path.join(frontend_app_dir, "utils")
    create_directory(utils_dir)
    create_init_file(os.path.join(utils_dir, "__init__.py"))
    create_python_file(os.path.join(utils_dir, "logger.py"), "Logging utilities")
    create_python_file(os.path.join(utils_dir, "file_utils.py"), "File utilities")
    
    # Frontend conf directory
    conf_dir = os.path.join(frontend_dir, "conf")
    create_directory(conf_dir)
    create_init_file(os.path.join(conf_dir, "__init__.py"))
    create_python_file(os.path.join(conf_dir, "config.py"), "Configuration with Hydra")
    
    # Frontend conf/config directory
    conf_config_dir = os.path.join(conf_dir, "config")
    create_directory(conf_config_dir)
    create_init_file(os.path.join(conf_config_dir, "__init__.py"))
    conf_config_files = [
        "default.yaml",
        "bot.yaml",
        "api.yaml",
    ]
    for file in conf_config_files:
        create_file(os.path.join(conf_config_dir, file))
    
    # Frontend tests directory
    tests_dir = os.path.join(frontend_dir, "tests")
    create_directory(tests_dir)
    create_init_file(os.path.join(tests_dir, "__init__.py"))
    create_python_file(os.path.join(tests_dir, "conftest.py"), "Pytest configuration")
    create_python_file(os.path.join(tests_dir, "test_bot.py"), "Tests for the bot")
    
    # Frontend test_handlers directory
    test_handlers_dir = os.path.join(tests_dir, "test_handlers")
    create_directory(test_handlers_dir)
    create_init_file(os.path.join(test_handlers_dir, "__init__.py"))
    create_python_file(os.path.join(test_handlers_dir, "test_admin_handlers.py"), "Tests for admin handlers")
    create_python_file(os.path.join(test_handlers_dir, "test_user_handlers.py"), "Tests for user handlers")
    
    # Frontend test_api directory
    test_api_dir = os.path.join(tests_dir, "test_api")
    create_directory(test_api_dir)
    create_init_file(os.path.join(test_api_dir, "__init__.py"))
    create_python_file(os.path.join(test_api_dir, "test_client.py"), "Tests for API client")
    
    # Backend structure
    backend_dir = os.path.join(root_dir, "backend")
    create_directory(backend_dir)
    
    # Backend app directory
    backend_app_dir = os.path.join(backend_dir, "app")
    create_directory(backend_app_dir)
    create_init_file(os.path.join(backend_app_dir, "__init__.py"))
    create_python_file(os.path.join(backend_app_dir, "main.py"), "Entry point for the backend application")
    
    # Backend api directory
    backend_api_dir = os.path.join(backend_app_dir, "api")
    create_directory(backend_api_dir)
    create_init_file(os.path.join(backend_api_dir, "__init__.py"))
    
    # Backend api routes directory
    api_routes_dir = os.path.join(backend_api_dir, "routes")
    create_directory(api_routes_dir)
    create_init_file(os.path.join(api_routes_dir, "__init__.py"))
    api_routes_files = [
        "languages.py",
        "users.py",
        "words.py",
        "statistics.py",
    ]
    for file in api_routes_files:
        create_python_file(os.path.join(api_routes_dir, file), f"Routes for {file.split('.')[0]}")
    
    # Backend api models directory
    backend_api_models_dir = os.path.join(backend_api_dir, "models")
    create_directory(backend_api_models_dir)
    create_init_file(os.path.join(backend_api_models_dir, "__init__.py"))
    backend_api_model_files = [
        "language.py",
        "user.py",
        "word.py",
        "statistics.py",
    ]
    for file in backend_api_model_files:
        create_python_file(os.path.join(backend_api_models_dir, file), f"API models for {file.split('.')[0]}")
    
    # Backend api schemas directory
    api_schemas_dir = os.path.join(backend_api_dir, "schemas")
    create_directory(api_schemas_dir)
    create_init_file(os.path.join(api_schemas_dir, "__init__.py"))
    api_schemas_files = [
        "language.py",
        "user.py",
        "word.py",
        "statistics.py",
    ]
    for file in api_schemas_files:
        create_python_file(os.path.join(api_schemas_dir, file), f"Pydantic schemas for {file.split('.')[0]}")
    
    # Backend db directory
    db_dir = os.path.join(backend_app_dir, "db")
    create_directory(db_dir)
    create_init_file(os.path.join(db_dir, "__init__.py"))
    create_python_file(os.path.join(db_dir, "database.py"), "Database configuration")
    
    # Backend db models directory
    db_models_dir = os.path.join(db_dir, "models")
    create_directory(db_models_dir)
    create_init_file(os.path.join(db_models_dir, "__init__.py"))
    db_models_files = [
        "language.py",
        "user.py",
        "word.py",
        "statistics.py",
    ]
    for file in db_models_files:
        create_python_file(os.path.join(db_models_dir, file), f"ORM models for {file.split('.')[0]}")
    
    # Backend db repositories directory
    db_repositories_dir = os.path.join(db_dir, "repositories")
    create_directory(db_repositories_dir)
    create_init_file(os.path.join(db_repositories_dir, "__init__.py"))
    create_python_file(os.path.join(db_repositories_dir, "base.py"), "Base repository")
    db_repo_files = [
        "language_repository.py",
        "user_repository.py",
        "word_repository.py",
        "statistics_repository.py",
    ]
    for file in db_repo_files:
        create_python_file(os.path.join(db_repositories_dir, file), f"Repository for {file.split('_')[0]}")
    
    # Backend services directory
    services_dir = os.path.join(backend_app_dir, "services")
    create_directory(services_dir)
    create_init_file(os.path.join(services_dir, "__init__.py"))
    service_files = [
        "language_service.py",
        "user_service.py",
        "word_service.py",
        "statistics_service.py",
        "excel_service.py",
    ]
    for file in service_files:
        create_python_file(os.path.join(services_dir, file), f"Service for {file.split('_')[0]}")
    
    # Backend core directory
    core_dir = os.path.join(backend_app_dir, "core")
    create_directory(core_dir)
    create_init_file(os.path.join(core_dir, "__init__.py"))
    create_python_file(os.path.join(core_dir, "config.py"), "Application configuration")
    create_python_file(os.path.join(core_dir, "exceptions.py"), "Custom exceptions")
    create_python_file(os.path.join(core_dir, "security.py"), "Security utilities")
    
    # Backend utils directory
    backend_utils_dir = os.path.join(backend_app_dir, "utils")
    create_directory(backend_utils_dir)
    create_init_file(os.path.join(backend_utils_dir, "__init__.py"))
    create_python_file(os.path.join(backend_utils_dir, "logger.py"), "Logging utilities")
    create_python_file(os.path.join(backend_utils_dir, "excel_parser.py"), "Excel parser utilities")
    
    # Backend conf directory
    backend_conf_dir = os.path.join(backend_dir, "conf")
    create_directory(backend_conf_dir)
    create_init_file(os.path.join(backend_conf_dir, "__init__.py"))
    create_python_file(os.path.join(backend_conf_dir, "config.py"), "Configuration with Hydra")
    
    # Backend conf/config directory
    backend_conf_config_dir = os.path.join(backend_conf_dir, "config")
    create_directory(backend_conf_config_dir)
    create_init_file(os.path.join(backend_conf_config_dir, "__init__.py"))
    backend_conf_config_files = [
        "default.yaml",
        "database.yaml",
        "api.yaml",
    ]
    for file in backend_conf_config_files:
        create_file(os.path.join(backend_conf_config_dir, file))
    
    # Backend alembic directory
    alembic_dir = os.path.join(backend_dir, "alembic")
    create_directory(alembic_dir)
    create_file(os.path.join(alembic_dir, "README"), "Alembic migrations")
    create_python_file(os.path.join(alembic_dir, "env.py"), "Alembic environment")
    create_file(os.path.join(alembic_dir, "script.py.mako"), "Alembic script template")
    
    # Backend alembic versions directory
    alembic_versions_dir = os.path.join(alembic_dir, "versions")
    create_directory(alembic_versions_dir)
    create_file(os.path.join(alembic_versions_dir, ".gitkeep"))
    
    # Backend tests directory
    backend_tests_dir = os.path.join(backend_dir, "tests")
    create_directory(backend_tests_dir)
    create_init_file(os.path.join(backend_tests_dir, "__init__.py"))
    create_python_file(os.path.join(backend_tests_dir, "conftest.py"), "Pytest configuration")
    
    # Backend test_api directory
    backend_test_api_dir = os.path.join(backend_tests_dir, "test_api")
    create_directory(backend_test_api_dir)
    create_init_file(os.path.join(backend_test_api_dir, "__init__.py"))
    backend_test_api_files = [
        "test_languages.py",
        "test_users.py",
        "test_words.py",
        "test_statistics.py",
    ]
    for file in backend_test_api_files:
        create_python_file(os.path.join(backend_test_api_dir, file), f"Tests for {file.split('_')[1].split('.')[0]} API")
    
    # Backend test_services directory
    test_services_dir = os.path.join(backend_tests_dir, "test_services")
    create_directory(test_services_dir)
    create_init_file(os.path.join(test_services_dir, "__init__.py"))
    test_service_files = [
        "test_language_service.py",
        "test_user_service.py",
        "test_word_service.py",
        "test_statistics_service.py",
    ]
    for file in test_service_files:
        create_python_file(os.path.join(test_services_dir, file), f"Tests for {file.split('_')[1].split('.')[0]} service")
    
    # Backend test_repositories directory
    test_repo_dir = os.path.join(backend_tests_dir, "test_repositories")
    create_directory(test_repo_dir)
    create_init_file(os.path.join(test_repo_dir, "__init__.py"))
    test_repo_files = [
        "test_language_repository.py",
        "test_user_repository.py",
        "test_word_repository.py",
        "test_statistics_repository.py",
    ]
    for file in test_repo_files:
        create_python_file(os.path.join(test_repo_dir, file), f"Tests for {file.split('_')[1].split('.')[0]} repository")
    
    print("Project structure created successfully!")

if __name__ == "__main__":
    main()