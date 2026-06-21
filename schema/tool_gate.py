import jsonschema
import json

class GovernanceValidationError(Exception):
    """
    Exception raised when a tool execution fails policy allowlist or payload schema checks.
    Outputs failure details as a structured JSON string.
    """
    def __init__(self, tool: str, reason: str, policy: str | None = None, rule: str | None = None):
        self.tool = tool
        self.reason = reason
        self.policy = policy
        self.rule = rule
        self.details = {
            "tool": tool,
            "status": "BLOCKED",
            "reason": reason
        }
        if policy:
            self.details["policy"] = policy
        if rule:
            self.details["rule"] = rule
        super().__init__(json.dumps(self.details))


# ==========================================
# STRICT JSON SCHEMAS FOR ALL 8 SYSTEM TOOLS
# ==========================================
SCHEMAS = {
    "proceed_transaction": {
        "type": "object",
        "properties": {
            "amount": {"type": "number", "minimum": 0.01},
            "recipient": {"type": "string", "minLength": 3, "maxLength": 100},
            "note": {"type": "string", "maxLength": 200},
            "data": {"type": "string", "maxLength": 200}
        },
        "required": ["amount", "recipient"],
        "additionalProperties": False
    },
    "send_email": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$"},
            "data": {"type": "string", "minLength": 1, "maxLength": 10000}
        },
        "required": ["to", "data"],
        "additionalProperties": False
    },
    "read_file": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "minLength": 1, "maxLength": 260},
            "path": {"type": "string", "minLength": 1, "maxLength": 260},
            "data": {"type": "string", "minLength": 1, "maxLength": 260}
        },
        "anyOf": [
            {"required": ["file_path"]},
            {"required": ["path"]},
            {"required": ["data"]}
        ],
        "additionalProperties": False
    },
    "write_file": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "minLength": 1, "maxLength": 260},
            "path": {"type": "string", "minLength": 1, "maxLength": 260},
            "content": {"type": "string", "maxLength": 100000},
            "data": {"type": "string", "maxLength": 100000}
        },
        "anyOf": [
            {"required": ["file_path", "content"]},
            {"required": ["path", "content"]},
            {"required": ["file_path", "data"]},
            {"required": ["path", "data"]}
        ],
        "additionalProperties": False
    },
    "delete_file": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "minLength": 1, "maxLength": 260},
            "path": {"type": "string", "minLength": 1, "maxLength": 260},
            "data": {"type": "string", "minLength": 1, "maxLength": 260}
        },
        "anyOf": [
            {"required": ["file_path"]},
            {"required": ["path"]},
            {"required": ["data"]}
        ],
        "additionalProperties": False
    },
    "execute_shell": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "minLength": 1, "maxLength": 500},
            "cmd": {"type": "string", "minLength": 1, "maxLength": 500},
            "data": {"type": "string", "minLength": 1, "maxLength": 500}
        },
        "anyOf": [
            {"required": ["command"]},
            {"required": ["cmd"]},
            {"required": ["data"]}
        ],
        "additionalProperties": False
    },
    "api_call": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "pattern": r"^https?://.+"},
            "data": {"type": "string", "pattern": r"^https?://.+"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
            "payload": {"type": "object"}
        },
        "anyOf": [
            {"required": ["url"]},
            {"required": ["data"]}
        ],
        "additionalProperties": False
    },
    "database_query": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 5, "maxLength": 1000},
            "sql": {"type": "string", "minLength": 5, "maxLength": 1000},
            "data": {"type": "string", "minLength": 5, "maxLength": 1000}
        },
        "anyOf": [
            {"required": ["query"]},
            {"required": ["sql"]},
            {"required": ["data"]}
        ],
        "additionalProperties": False
    }
}


class ToolAuthorityGate:
    """
    Enforces allow/deny constraints on registered system tools
    and validates invocation payloads against strict JSON schemas.
    """
    def __init__(self, contracts):
        self.contracts = contracts
    
    def validate_tool(self, tool_name: str) -> bool:
        """
        Asserts that a tool is explicitly permitted by the active IntentContract.
        """
        policy_str = None
        if hasattr(self.contracts, "policy_id") and self.contracts.policy_id:
            version_suffix = f"_v{self.contracts.policy_version}" if self.contracts.policy_version else ""
            policy_str = f"{self.contracts.policy_id}{version_suffix}"

        if tool_name in self.contracts.forbidden_tools:
            reason = f"Tool '{tool_name}' is explicitly forbidden by contract"
            if policy_str:
                reason = f"Tool '{tool_name}' forbidden by active policy '{policy_str}'"
            raise GovernanceValidationError(
                tool=tool_name,
                reason=reason,
                policy=policy_str,
                rule="forbidden_tools"
            )
            
        if tool_name not in self.contracts.allowed_tools:
            reason = f"Tool '{tool_name}' is not allowed by contract intent"
            if policy_str:
                reason = f"Tool '{tool_name}' not allowed by active policy '{policy_str}'"
            raise GovernanceValidationError(
                tool=tool_name,
                reason=reason,
                policy=policy_str,
                rule="allowed_tools"
            )

        print("Tool authorization validation succeeded")
        return True

    def validate_schema(self, tool_name: str, payload: dict) -> bool:
        """
        Asserts that a tool's payload matches its registered schema parameters.
        Rejects calls by default if no schema is configured.
        """
        policy_str = None
        if hasattr(self.contracts, "policy_id") and self.contracts.policy_id:
            version_suffix = f"_v{self.contracts.policy_version}" if self.contracts.policy_version else ""
            policy_str = f"{self.contracts.policy_id}{version_suffix}"

        if tool_name not in SCHEMAS:
            raise GovernanceValidationError(
                tool=tool_name,
                reason=f"Schema validation rejected: No registered schema for tool '{tool_name}'",
                policy=policy_str,
                rule="schema_validation"
            )

        schema = SCHEMAS[tool_name]
        try:
            jsonschema.validate(instance=payload, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            raise GovernanceValidationError(
                tool=tool_name,
                reason=f"Schema validation failed: {e.message}",
                policy=policy_str,
                rule="schema_validation"
            )

        print("Tool schema validation succeeded")
        return True
