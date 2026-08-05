class DemoOrderServiceError(Exception):
    """Base exception for expected demo-service failures."""


class PaymentTimeoutError(DemoOrderServiceError):
    pass


class PaymentDeclinedError(DemoOrderServiceError):
    pass


class PaymentProviderError(DemoOrderServiceError):
    pass


class MissingConfigurationError(DemoOrderServiceError):
    pass


class BackgroundJobFailureError(DemoOrderServiceError):
    pass

