"""Error handling and logging utilities."""

import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from functools import wraps

from .logger import get_logger


class DevelopmentErrorLogger:
    """Logger for development errors that writes to a file."""
    
    def __init__(self, log_file: str = "development_errors.log"):
        self.log_file = Path(log_file)
        self.logger = get_logger(__name__)
        
    def log_error(self, module: str, error_type: str, description: str, 
                  solution: Optional[str] = None, exception: Optional[Exception] = None):
        """Log an error to the development errors file.
        
        Args:
            module: Module where the error occurred
            error_type: Type of error (e.g., APIError, ConfigError)
            description: Description of the error
            solution: Solution applied (if any)
            exception: The exception object (if any)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build error entry
        error_entry = f"\n[{timestamp}] [{module}] [{error_type}] {description}"
        
        if exception:
            error_entry += f"\nException: {type(exception).__name__}: {str(exception)}"
            error_entry += f"\nTraceback:\n{traceback.format_exc()}"
            
        if solution:
            error_entry += f"\nSolution Applied: {solution}"
            
        error_entry += "\n" + "-" * 80
        
        # Write to file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(error_entry + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write to error log: {e}")
            
        # Also log to standard logger
        self.logger.error(f"[{module}] {error_type}: {description}")


# Global error logger instance
dev_error_logger = DevelopmentErrorLogger()


def handle_errors(module: str):
    """Decorator to handle and log errors in functions.
    
    Args:
        module: Module name for error logging
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error
                dev_error_logger.log_error(
                    module=module,
                    error_type=type(e).__name__,
                    description=f"Error in {func.__name__}",
                    exception=e
                )
                # Re-raise the exception
                raise
        return wrapper
    return decorator


class RetryHandler:
    """Handle retries with exponential backoff."""
    
    def __init__(self, max_attempts: int = 3, backoff_factor: float = 2.0, 
                 max_backoff: int = 60):
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.logger = get_logger(__name__)
        
    def retry(self, func, *args, **kwargs) -> Any:
        """Retry a function with exponential backoff.
        
        Args:
            func: Function to retry
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: If all retry attempts fail
        """
        import time
        
        last_exception = None
        wait_time = 1
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                    wait_time = min(wait_time * self.backoff_factor, self.max_backoff)
                else:
                    self.logger.error(f"All {self.max_attempts} attempts failed.")
                    
        if last_exception:
            raise last_exception