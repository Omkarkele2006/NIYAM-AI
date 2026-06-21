print("INTENT CONTRACT MODULE LOADED")

import hashlib
import json
import uuid
from pydantic import BaseModel, Field, PrivateAttr
from typing import List


class IntentContract(BaseModel):
    agent_name: str
    user_task: str
    allowed_tools: List[str]
    forbidden_tools: List[str]
    policy_id: str | None = None
    policy_version: str | None = None

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Internal state (not model fields)
    _sealed: bool = PrivateAttr(default=False)
    _sealed_hash: str = PrivateAttr(default=None)

    def generate_intent_hash(self) -> str:
        normalized = json.dumps(
            {
                "agent_name": self.agent_name,
                "user_task": self.user_task,
                "allowed_tools": sorted(self.allowed_tools),
                "forbidden_tools": sorted(self.forbidden_tools),
            },
            sort_keys=True,
        )
        return hashlib.sha256(normalized.encode()).hexdigest()

    def seal(self):
        if self._sealed:
            raise Exception("IntentContract is already sealed.")

        print("Sealing contract...")

        # Store hash
        self._sealed_hash = self.generate_intent_hash()

        # Convert lists to tuples (IMMUTABLE)
        object.__setattr__(self, "allowed_tools", tuple(self.allowed_tools))
        object.__setattr__(self, "forbidden_tools", tuple(self.forbidden_tools))

        self._sealed = True

    def intent_hash(self):
        if self._sealed:
            return self._sealed_hash
        return self.generate_intent_hash()

    def __setattr__(self, name, value):
        if hasattr(self, "_sealed") and self._sealed:
            if name in {"allowed_tools", "forbidden_tools", "user_task", "agent_name"}:
                raise Exception("IntentContract is sealed and cannot be modified.")
        super().__setattr__(name, value)