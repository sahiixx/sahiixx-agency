"""Safety-hardened adapter for the T3MP3ST red-team framework."""

from __future__ import annotations

import hmac
from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.adapters.security._t3mp3st_validation import validate_target
from sahiixx_agency.core.models import RepoNode


class T3mp3stAdapter(BaseAdapter):
    """Adapter for T3MP3ST with target scoping and arsenal gating."""

    def __init__(
        self,
        clone_base_dir: str = "./data/repos",
        approval_token: str | None = None,
        network_policy: Any = None,
        audit_logger: Any = None,
    ) -> None:
        super().__init__(clone_base_dir=clone_base_dir, network_policy=network_policy, audit_logger=audit_logger)
        self.approval_token = approval_token

    def _validate_payload(
        self,
        payload: dict[str, Any],
        *,
        blocked_networks: list[str] | None = None,
        allow_local: bool | None = None,
    ) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
        """Validate payload and build the safety environment dict.

        Returns ``(env, error)``. ``env`` is ``None`` when validation fails.
        """
        target = payload.get("target")
        mode = payload.get("mode", "lite")
        approval = payload.get("approval")
        payload_allow_local = payload.get("allow_local")
        if payload_allow_local is not None:
            allow_local = bool(payload_allow_local)
        elif allow_local is None:
            allow_local = False
        else:
            allow_local = bool(allow_local)

        if not isinstance(target, str) or not target.strip():
            return None, {
                "status": "validation_error",
                "error_code": "missing_target",
                "message": "target must be a non-empty string",
            }

        if mode not in {"lite", "full"}:
            return None, {
                "status": "validation_error",
                "error_code": "invalid_mode",
                "message": "mode must be 'lite' or 'full'",
            }

        error = validate_target(target, allow_local=allow_local, blocked_networks=blocked_networks)
        if error:
            return None, {
                "status": "validation_error",
                "error_code": error,
                "message": f"Target '{target}' failed validation: {error}",
            }

        full_arsenal = "0"
        if mode == "full":
            if not self.approval_token:
                return None, {
                    "status": "validation_error",
                    "error_code": "approval_not_configured",
                    "message": "Full arsenal requested but no approval token is configured in OPA.",
                }
            if not isinstance(approval, str):
                return None, {
                    "status": "validation_error",
                    "error_code": "approval_required",
                    "message": "Full arsenal requested but approval token must be a string.",
                }
            if not hmac.compare_digest(approval, self.approval_token):
                return None, {
                    "status": "validation_error",
                    "error_code": "approval_mismatch",
                    "message": "Full arsenal requested but approval token is invalid.",
                }
            full_arsenal = "1"

        env: dict[str, str] = {
            "T3MP3ST_TARGET": target,
            "T3MP3ST_FULL_ARSENAL": full_arsenal,
            "T3MP3ST_EGRESS_POLICY": "scoped",
        }
        return env, None

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        blocked_networks = module.adapter_config.get("blocked_targets")
        env, error = self._validate_payload(
            payload,
            blocked_networks=blocked_networks,
            allow_local=module.adapter_config.get("allow_local"),
        )
        if error:
            return error

        run_payload = {
            "command": payload.get("command", "run"),
            "env": env,
            "timeout": payload.get("timeout", 180),
        }
        result = await super().run(module, run_payload)
        result["t3mp3st_mode"] = payload.get("mode", "lite")
        result["t3mp3st_target"] = payload["target"]
        return result
