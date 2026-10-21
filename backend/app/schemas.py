from pydantic import BaseModel


class CommandRequest(BaseModel):
    command: str


class DeviceUpdate(BaseModel):
    manual_offline: bool
