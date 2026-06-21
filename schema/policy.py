import json
import re
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Set
from schema.tool_gate import SCHEMAS

REPO_ROOT = Path(__file__).resolve().parents[1]


class PolicyValidationError(ValueError):
    """Exception raised when a policy fails schema or rule validations."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Policy validation failed: {'; '.join(errors)}")


class Policy(BaseModel):
    """Data representation of a Governance Policy Artifact."""
    policy_id: str
    version: str
    status: str = "draft"  # "active", "inactive", "draft"
    created_at: str
    description: str
    allowed_tools: List[str]
    forbidden_tools: List[str]
    constraints: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def policy_hash(self) -> str:
        """Compute a deterministic SHA-256 hash of the policy JSON content."""
        import hashlib
        normalized = json.dumps(
            self.dict(),
            sort_keys=True
        )
        return hashlib.sha256(normalized.encode()).hexdigest()

    def to_contract(self, agent_name: str, user_task: str) -> Any:
        """Convert this policy artifact into a runtime IntentContract."""
        from schema.intent_contract import IntentContract
        contract = IntentContract(
            agent_name=agent_name,
            user_task=user_task,
            allowed_tools=self.allowed_tools,
            forbidden_tools=self.forbidden_tools
        )
        # Store metadata inside the Pydantic instance securely (pure domain model fields)
        contract.policy_id = self.policy_id
        contract.policy_version = self.version
        return contract


def validate_policy_data(data: dict, valid_tools: Set[str] | None = None) -> List[str]:
    """Validate raw policy fields and logical constraints."""
    errors = []

    # 1. Required fields
    required_fields = ["policy_id", "version", "status", "created_at", "description", "allowed_tools", "forbidden_tools"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field '{field}'")

    if errors:
        return errors  # Halt validation early if basic schema structure is missing

    # 2. Version format validation
    version = data["version"]
    if not isinstance(version, str):
        errors.append("Version must be a string")
    elif not re.match(r"^\d+\.\d+(\.\d+)?$", version):
        errors.append(f"Invalid version format '{version}'. Must match semantic version format (e.g. 1.0 or 1.0.0)")

    # 3. Status validation
    status = data["status"]
    if status not in {"active", "inactive", "draft"}:
        errors.append(f"Invalid status '{status}'. Must be 'active', 'inactive', or 'draft'")

    # 4. Duplicate checks
    allowed = data["allowed_tools"]
    forbidden = data["forbidden_tools"]

    if not isinstance(allowed, list):
        errors.append("allowed_tools must be a list")
    else:
        duplicates_allowed = {x for x in allowed if allowed.count(x) > 1}
        if duplicates_allowed:
            errors.append(f"Duplicate tools in allowed_tools: {sorted(list(duplicates_allowed))}")

    if not isinstance(forbidden, list):
        errors.append("forbidden_tools must be a list")
    else:
        duplicates_forbidden = {x for x in forbidden if forbidden.count(x) > 1}
        if duplicates_forbidden:
            errors.append(f"Duplicate tools in forbidden_tools: {sorted(list(duplicates_forbidden))}")

    # 5. Conflicting rules check
    if isinstance(allowed, list) and isinstance(forbidden, list):
        conflicts = set(allowed) & set(forbidden)
        if conflicts:
            errors.append(f"Conflicting tools declared in both allowed and forbidden lists: {sorted(list(conflicts))}")

    # 6. Constraints validation
    constraints = data.get("constraints", {})
    if not isinstance(constraints, dict):
        errors.append("constraints must be a JSON object (dictionary)")

    # 7. Invalid tool references check against registry / gate schemas
    if valid_tools is None:
        valid_tools = set(SCHEMAS.keys())

    if isinstance(allowed, list):
        for tool in allowed:
            if tool not in valid_tools:
                errors.append(f"Tool '{tool}' listed in allowed_tools is not registered in the system")

    if isinstance(forbidden, list):
        for tool in forbidden:
            if tool not in valid_tools:
                errors.append(f"Tool '{tool}' listed in forbidden_tools is not registered in the system")

    return errors


class PolicyRepository:
    """Repository Layer managing access, persistence, and versioning of policies."""
    def __init__(self, directory: str | Path | None = None):
        if directory:
            self.directory = Path(directory)
        else:
            self.directory = REPO_ROOT / "policies"
        self.directory.mkdir(parents=True, exist_ok=True)

    def validate_policy(self, data: dict, valid_tools: Set[str] | None = None) -> List[str]:
        return validate_policy_data(data, valid_tools)

    def load_policy_from_dict(self, data: dict, valid_tools: Set[str] | None = None) -> Policy:
        errors = self.validate_policy(data, valid_tools)
        if errors:
            raise PolicyValidationError(errors)
        return Policy(**data)

    def load_policy(self, policy_id_or_path: str | Path, version: str | None = None, valid_tools: Set[str] | None = None) -> Policy:
        """
        Load a policy by ID/Path and optional version.
        If a file path is provided, loads it. If an ID is provided, searches the repository.
        """
        path = Path(policy_id_or_path)
        if not path.is_file() and not path.suffix:
            # It's an ID
            policy_id = str(policy_id_or_path)
            if version:
                path = self.directory / f"{policy_id}_v{version}.json"
            else:
                # Find active version
                active_policy = self.get_active_policy(policy_id)
                if active_policy:
                    return active_policy
                else:
                    # Fallback to latest version
                    versions = self.retrieve_versions(policy_id)
                    if not versions:
                        raise FileNotFoundError(f"No policy versions found for policy ID '{policy_id}'")
                    return versions[-1]

        if not path.exists():
            raise FileNotFoundError(f"Policy file not found at '{path}'")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self.load_policy_from_dict(data, valid_tools)

    def list_policies(self) -> Dict[str, List[Policy]]:
        """Return a mapping of policy_id to lists of all stored versions, sorted ascending."""
        policies = {}
        for path in self.directory.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                policy = Policy(**data)
                if policy.policy_id not in policies:
                    policies[policy.policy_id] = []
                policies[policy.policy_id].append(policy)
            except Exception:
                pass

        for p_id in policies:
            policies[p_id].sort(key=lambda p: self._version_key(p.version))

        return policies

    def get_active_policy(self, policy_id: str) -> Optional[Policy]:
        """Find the active version of a policy."""
        versions = self.retrieve_versions(policy_id)
        for p in versions:
            if p.status == "active":
                return p
        return None

    def retrieve_versions(self, policy_id: str) -> List[Policy]:
        """Retrieve all versions of a policy ID, sorted ascending."""
        all_policies = self.list_policies()
        return all_policies.get(policy_id, [])

    def save_policy(self, policy: Policy, overwrite: bool = False) -> Path:
        """
        Save a policy version to the policies directory.
        Enforces immutability: raises FileExistsError if the file exists and overwrite=False.
        """
        filename = f"{policy.policy_id}_v{policy.version}.json"
        dest_path = self.directory / filename

        if dest_path.exists() and not overwrite:
            raise FileExistsError(
                f"Policy version immutability violated: policy file '{filename}' already exists."
            )

        # Re-validate before saving
        errors = self.validate_policy(policy.dict())
        if errors:
            raise PolicyValidationError(errors)

        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(policy.dict(), f, indent=2)

        return dest_path

    def _version_key(self, version_str: str) -> tuple:
        """Helper to convert version string into tuple of integers for sorting."""
        parts = version_str.split(".")
        try:
            return tuple(int(x) for x in parts)
        except ValueError:
            return (0,)


def compare_versions(p1: Policy, p2: Policy) -> dict:
    """Compare two policy versions and produce a deterministic structured diff."""
    diff = {
        "policy_id": p1.policy_id,
        "from_version": p1.version,
        "to_version": p2.version,
        "added_allowed_tools": sorted(list(set(p2.allowed_tools) - set(p1.allowed_tools))),
        "removed_allowed_tools": sorted(list(set(p1.allowed_tools) - set(p2.allowed_tools))),
        "added_forbidden_tools": sorted(list(set(p2.forbidden_tools) - set(p1.forbidden_tools))),
        "removed_forbidden_tools": sorted(list(set(p1.forbidden_tools) - set(p2.forbidden_tools))),
    }

    if p1.status != p2.status:
        diff["changed_status"] = {"from": p1.status, "to": p2.status}
    if p1.description != p2.description:
        diff["changed_description"] = {"from": p1.description, "to": p2.description}

    # Compare constraints
    added_constraints = {}
    removed_constraints = {}
    modified_constraints = {}

    for k, v in p2.constraints.items():
        if k not in p1.constraints:
            added_constraints[k] = v
        elif p1.constraints[k] != v:
            modified_constraints[k] = {"from": p1.constraints[k], "to": v}

    for k, v in p1.constraints.items():
        if k not in p2.constraints:
            removed_constraints[k] = v

    if added_constraints or removed_constraints or modified_constraints:
        diff["changed_constraints"] = {
            "added": added_constraints,
            "removed": removed_constraints,
            "modified": modified_constraints,
        }

    return diff
