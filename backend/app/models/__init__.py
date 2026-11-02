"""Toàn bộ bảng của app. Thêm bảng mới: tạo class trong file phù hợp và import ở đây,
rồi chạy `uv run python manage.py make "mô tả"` + `uv run python manage.py migrate`."""

from app.models.base import Base
from app.models.users import Device, Notification, NotificationDelivery, Profile, UserSetting
from app.models.agents import Agent, GoclawWorkspace, UserAgentAccess
from app.models.chat import Conversation, Message, MessageAttachment
from app.models.tasks import OutboxEvent, ScheduledTask, ScheduledTaskLog, ScheduledTaskRun, SocialAccount

__all__ = [
    "Base",
    "Profile",
    "UserSetting",
    "Device",
    "Notification",
    "NotificationDelivery",
    "GoclawWorkspace",
    "Agent",
    "UserAgentAccess",
    "Conversation",
    "Message",
    "MessageAttachment",
    "SocialAccount",
    "ScheduledTask",
    "ScheduledTaskRun",
    "ScheduledTaskLog",
    "OutboxEvent",
]
