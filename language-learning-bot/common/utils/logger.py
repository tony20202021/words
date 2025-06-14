"""
Unified logging utilities for Language Learning Bot.

This module provides setup functions for configuring application logging,
supporting both console and file output with customizable log levels.
It is shared between frontend and backend components.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Union


def setup_logger(
    name: str, 
    log_level: Union[int, str] = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "logs",
    log_format: str = None,
    log_file_max_size: int = 5 * 1024 * 1024,  # 5 MB
    log_file_backup_count: int = 3,
) -> logging.Logger:
    """
    Set up and configure a logger with custom formatting and handlers.
    
    Args:
        name: Name of the logger, typically the module name using __name__
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to a file or not
        log_dir: Directory to store log files
        log_format: Custom format for log messages (optional)
        log_file_max_size: Maximum size of log file before rotation in bytes
        log_file_backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Convert string log level to its numeric value if needed
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger instance
    logger = logging.getLogger(name)
    
    # Only configure logger if it hasn't been configured already
    if not logger.handlers:
        logger.setLevel(log_level)
        
        # Format for log messages
        default_format = '%(asctime)s{%(levelname)s}[%(filename)s:%(lineno)d]: %(message)s'
        format_str = log_format if log_format else default_format
        
        formatter = logging.Formatter(
            format_str,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Setup file handler if requested
        if log_to_file:
            try:
                # Create log directory if it doesn't exist
                os.makedirs(log_dir, exist_ok=True)
                
                # Determine log filename based on module name
                log_filename = os.path.join(log_dir, f"{name.split('.')[-1]}.log")
                
                # Create rotating file handler
                file_handler = RotatingFileHandler(
                    log_filename,
                    maxBytes=log_file_max_size,
                    backupCount=log_file_backup_count
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                # Log error but continue without file logging
                logger.error(f"Failed to setup file logging: {e}")
                logger.warning("Continuing with console logging only")
    
    return logger


def get_module_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module, using the default configuration.
    
    Args:
        module_name: Name of the module, typically __name__
        
    Returns:
        Configured logger instance
    """
    return setup_logger(module_name)