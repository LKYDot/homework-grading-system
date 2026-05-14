class BusinessException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(self.message)


class ValidationException(BusinessException):
    def __init__(self, message: str = "数据验证失败"):
        super().__init__(code=400, message=message)


class NotFoundException(BusinessException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=404, message=message)


class UnauthorizedException(BusinessException):
    def __init__(self, message: str = "未授权"):
        super().__init__(code=401, message=message)


class ForbiddenException(BusinessException):
    def __init__(self, message: str = "禁止访问"):
        super().__init__(code=403, message=message)


__all__ = [
    "BusinessException",
    "ValidationException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
]
