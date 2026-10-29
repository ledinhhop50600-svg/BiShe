"""接口层：审核 / 预检（对应 docs/设计文档/Agent接口契约-v1.md 的接口一）。"""

from fastapi import APIRouter, Header

from api.common import check_token
from judge import judge
from replay import load as replay_load
from replay import save as replay_save
from schemas import AuditRequest, AuditResponse

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/audit", response_model=AuditResponse)
def audit(req: AuditRequest, x_agent_token: str = Header(default="")) -> AuditResponse:
    check_token(x_agent_token)

    # ---- 1) 回放：同一 requestId 直接命中缓存 ----
    cached = replay_load(req.requestId)
    if cached is not None:
        cached["replayed"] = True
        return AuditResponse(**cached)

    # 敏感词库作为词面来源（规则示例词 + 敏感词），补上"短语对不上正文"的缺口
    extra_terms = [w.get("word", "") for w in (req.sensitiveWords or []) if w.get("word")]

    # ---- 2) 判定（与阶段 6 的适配后合规预检共用同一套逻辑）----
    response = judge(req, extra_terms=extra_terms,
                     use_rag=req.useRag, localize_flag=bool(req.localize))

    # ---- 3) 写入回放缓存（之后再调同一 requestId 会直接命中）----
    replay_save(req.requestId, response.model_dump())

    return response
