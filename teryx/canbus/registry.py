"""All known CAN messages by id."""

from .codec import Message
from .messages import TERYX_MESSAGES
from .shinegle import SHINEGLE_MESSAGES

ALL_MESSAGES: tuple[Message, ...] = SHINEGLE_MESSAGES + TERYX_MESSAGES
BY_ID: dict[int, Message] = {m.can_id: m for m in ALL_MESSAGES}
BY_NAME: dict[str, Message] = {m.name: m for m in ALL_MESSAGES}
assert len(BY_ID) == len(ALL_MESSAGES), "duplicate CAN id"
