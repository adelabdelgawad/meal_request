class AppError(Exception):
    pass


class AuthenticationError(AppError):
    pass


class AuthorizationError(AppError):
    pass


class DatabaseError(AppError):
    pass
