#!/usr/bin/env python
"""
Script for watching file changes and automatically reloading the bot.
This script monitors the specified directories for changes and
restarts the bot when files are modified.
"""

import time
import subprocess
import os
import sys
import signal
import argparse
import logging
from pathlib import Path
from typing import List, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("watch_and_reload")

class BotProcess:
    """Class to manage the bot process."""
    
    def __init__(self, script_path: str, process_name: str):
        """
        Initialize the bot process.
        
        Args:
            script_path: Path to the bot script
            process_name: Name of the process for identification
        """
        self.script_path = script_path
        self.process_name = process_name
        self.process = None
        self.running = False
    
    def start(self) -> None:
        """Start the bot process."""
        if self.running:
            logger.info("Process is already running. Skipping start.")
            return
            
        try:
            logger.info(f"Starting bot process: {self.script_path}")
            # Запускаем процесс с передачей идентификатора
            self.process = subprocess.Popen(
                ["python", self.script_path, f"--process-name={self.process_name}"],
                # Перенаправляем вывод в текущую консоль
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            self.running = True
            logger.info(f"Bot process started with PID: {self.process.pid}")
        except Exception as e:
            logger.error(f"Failed to start bot process: {e}")
    
    def stop(self) -> None:
        """Stop the bot process."""
        if not self.running or not self.process:
            logger.info("No running process to stop.")
            return
            
        try:
            logger.info(f"Stopping bot process with PID: {self.process.pid}")
            
            # Отправляем SIGTERM для корректного завершения
            self.process.send_signal(signal.SIGTERM)
            
            # Даем процессу время на корректное завершение
            for _ in range(5):  # 5 секунд ожидания
                if self.process.poll() is not None:
                    break
                time.sleep(1)
            
            # Если процесс все еще работает, принудительно завершаем
            if self.process.poll() is None:
                logger.warning("Process did not terminate gracefully. Sending SIGKILL.")
                self.process.kill()
                self.process.wait()
            
            self.running = False
            logger.info("Bot process stopped successfully.")
        except Exception as e:
            logger.error(f"Error stopping bot process: {e}")
            # В случае ошибки все равно считаем процесс завершенным
            self.running = False
    
    def restart(self) -> None:
        """Restart the bot process."""
        logger.info("Restarting bot process...")
        self.stop()
        # Небольшая пауза перед запуском для завершения всех подпроцессов
        # time.sleep(2)
        self.start()
        time.sleep(5)


class ChangeHandler(FileSystemEventHandler):
    """Handler for file system events."""
    
    def __init__(self, bot_process: BotProcess, watch_extensions: List[str], ignore_dirs: List[str]):
        """
        Initialize the change handler.
        
        Args:
            bot_process: Bot process to manage
            watch_extensions: List of file extensions to watch
            ignore_dirs: List of directories to ignore
        """
        self.bot_process = bot_process
        self.watch_extensions = watch_extensions
        self.ignore_dirs = ignore_dirs
        self.last_modified_time = time.time()
        # Минимальный интервал между перезапусками (в секундах)
        self.throttle_interval = 10
    
    def should_process_event(self, event) -> bool:
        """
        Check if the event should be processed.
        
        Args:
            event: File system event
        
        Returns:
            True if the event should be processed, False otherwise
        """
        # Проверяем, прошло ли достаточно времени с последнего события
        current_time = time.time()
        if current_time - self.last_modified_time < self.throttle_interval:
            return False
            
        # Проверяем, является ли событие модификацией или созданием файла
        if not isinstance(event, (FileModifiedEvent, FileCreatedEvent)):
            return False
            
        # Проверяем расширение файла
        if not any(event.src_path.endswith(ext) for ext in self.watch_extensions):
            return False
            
        # Проверяем, не находится ли файл в игнорируемой директории
        if any(ignore_dir in event.src_path for ignore_dir in self.ignore_dirs):
            return False
            
        return True
    
    def on_modified(self, event):
        """
        Handle the file modification event.
        
        Args:
            event: File system modification event
        """
        if self.should_process_event(event):
            logger.info(f"Detected change in file: {event.src_path}")
            self.last_modified_time = time.time()
            self.bot_process.restart()
    
    def on_created(self, event):
        """
        Handle the file creation event.
        
        Args:
            event: File system creation event
        """
        if self.should_process_event(event):
            logger.info(f"Detected new file: {event.src_path}")
            self.last_modified_time = time.time()
            self.bot_process.restart()


def run_watcher(
    script_path: str,
    watch_paths: List[str],
    process_name: str = "frontend_autoreload",
    watch_extensions: Optional[List[str]] = None,
    ignore_dirs: Optional[List[str]] = None
) -> None:
    """
    Run the file watcher.
    
    Args:
        script_path: Path to the bot script
        watch_paths: List of directories to watch
        process_name: Name of the process for identification
        watch_extensions: List of file extensions to watch
        ignore_dirs: List of directories to ignore
    """
    if watch_extensions is None:
        watch_extensions = ['.py', '.yaml', '.yml']
        
    if ignore_dirs is None:
        ignore_dirs = [
            '__pycache__', 
            '.git', 
            'env', 
            'venv', 
            '.env', 
            '.venv', 
            'logs',
            'node_modules'
        ]
    
    logger.info(f"Starting watcher for script: {script_path}")
    logger.info(f"Watching directories: {watch_paths}")
    logger.info(f"Watching for changes in files with extensions: {watch_extensions}")
    logger.info(f"Ignoring directories: {ignore_dirs}")
    
    # Initialize the bot process manager
    bot_process = BotProcess(script_path, process_name)
    
    # Initialize the event handler
    event_handler = ChangeHandler(bot_process, watch_extensions, ignore_dirs)
    
    # Initialize the observer
    observer = Observer()
    
    # Schedule watching of directories
    for path in watch_paths:
        path_obj = Path(path)
        if path_obj.exists() and path_obj.is_dir():
            observer.schedule(event_handler, path, recursive=True)
            logger.info(f"Watching directory: {path}")
        else:
            logger.warning(f"Directory not found: {path}")
    
    # Start the observer
    observer.start()
    
    # Start the bot initially
    bot_process.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Stopping...")
        bot_process.stop()
        observer.stop()
    
    # Wait for the observer to finish
    observer.join()
    logger.info("Watcher stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Watch for file changes and reload bot')
    parser.add_argument(
        '--script',
        type=str,
        default='app/main_frontend.py',
        help='Path to the bot script'
    )
    parser.add_argument(
        '--paths',
        type=str,
        nargs='+',
        default=['app'],
        help='Directories to watch for changes'
    )
    parser.add_argument(
        '--process-name',
        type=str,
        default='frontend_autoreload',
        help='Name of the process for identification'
    )
    parser.add_argument(
        '--extensions',
        type=str,
        nargs='+',
        default=['.py', '.yaml', '.yml'],
        help='File extensions to watch'
    )
    parser.add_argument(
        '--ignore-dirs',
        type=str,
        nargs='+',
        default=['__pycache__', '.git', 'env', 'venv', '.env', '.venv', 'logs'],
        help='Directories to ignore'
    )
    
    args = parser.parse_args()
    
    run_watcher(
        script_path=args.script,
        watch_paths=args.paths,
        process_name=args.process_name,
        watch_extensions=args.extensions,
        ignore_dirs=args.ignore_dirs
    )