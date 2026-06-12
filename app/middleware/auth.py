"""认证中间件骨架 — Phase 1 为空实现，预留扩展点。"""
from fastapi import Request


def verify_api_key():
    """依赖注入：校验 X-API-Key Header。
    Phase 1 实现为空（始终通过）。
    """

    async def _verify(request: Request) -> None:
        _ = request.headers.get("X-API-Key")  # Phase 1 placeholder -- no-op

    return _verify
