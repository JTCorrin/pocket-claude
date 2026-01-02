"""
Custom exception classes for the application.
"""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(self, message: str = "Bad request"):
        super().__init__(message, status_code=400)


class UnauthorizedException(AppException):
    """Unauthorized exception."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenException(AppException):
    """Forbidden exception."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class ServiceUnavailableException(AppException):
    """Service unavailable exception - for external service failures."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, status_code=503)


class CommandTimeoutException(ServiceUnavailableException):
    """Command execution timeout exception."""

    def __init__(self, message: str = "Command execution timed out"):
        super().__init__(message)


class CLINotFoundException(ServiceUnavailableException):
    """Claude CLI not found exception."""

    def __init__(self, message: str = "Claude CLI not found. Please ensure it is installed."):
        super().__init__(message)


class FileSystemException(AppException):
    """File system operation exception."""

    def __init__(self, message: str = "File system operation failed"):
        super().__init__(message, status_code=500)
