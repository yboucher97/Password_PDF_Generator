class WifiPdfError(Exception):
    """Base error for the WiFi PDF pipeline."""


class ConfigurationError(WifiPdfError):
    """Raised when config or environment is invalid."""


class PayloadValidationError(WifiPdfError):
    """Raised when inbound JSON does not match the expected model."""


class RenderingError(WifiPdfError):
    """Raised when QR or PDF generation fails."""


class WorkDriveError(WifiPdfError):
    """Raised when Zoho WorkDrive upload fails."""
