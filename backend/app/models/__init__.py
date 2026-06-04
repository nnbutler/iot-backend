# Import all models so SQLAlchemy can discover them
from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.device import Device, DeviceLog, DeviceErrorHistory, MqttCredential  # noqa: F401
from app.models.error import ErrorType, RepairAction, RepairOutcome  # noqa: F401
from app.models.command import Command  # noqa: F401
