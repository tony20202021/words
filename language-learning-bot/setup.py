#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="language-learning-bot",
    version="0.1.0",
    description="Telegram bot for learning foreign languages",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/username/language-learning-bot",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.8",
    install_requires=[
        # Dependencies are defined in requirements.txt
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.10.0",
            "black>=23.3.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "lang-bot-frontend=frontend.app.main:main",
            "lang-bot-backend=backend.app.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)