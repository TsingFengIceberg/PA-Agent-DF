"""Adversarial critique protocol message models.

四权分立：
- Critic 发出 Challenge（必须附带证据，不可自行采集）
- Scout 返回 Rebuttal（附带新数据，不是纯文字辩解）
- Meta-Judge 做出 Ruling（基于计算验证，不看身份）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Challenge 严重程度——决定是否需要中止当前研究。"""
    CRITICAL = "critical"  # 数据源冲突，可能推翻核心结论
    MAJOR = "major"        # 数据不一致，需要定向补采
    MINOR = "minor"        # 格式/时效性问题，不阻塞流程


class Verdict(str, Enum):
    """Meta-Judge 的裁定结果。"""
    RESOLVED = "resolved"          # 经补采已解决
    UNRESOLVED = "unresolved"      # 2 轮内无法解决，标记遗留
    DISMISSED = "dismissed"        # 质疑本身无效（证据不足）


@dataclass
class Challenge:
    """Critic Agent 对抗式质疑。

    每一条质疑必须附带 evidence（引用具体数据点、来源对比）。
    Critic 不可自行采集新数据——只能基于已有 scout_results 进行质疑。
    """

    challenge_id: str
    claim: str
    """被质疑的具体主张，如 'scout_A 报告的 iPhone 17 价格<$6999 与其他来源矛盾'。"""

    evidence: list[dict[str, Any]]
    """质疑证据列表，每条至少包含 type/source/data 字段。

    示例: [{"type": "source_conflict", "source": "IDC 2026Q1",
            "data": "IDC 报告显示价格为 $7199", "vs": "apple.com 显示 $6999"}]
    """

    severity: Severity
    suggested_remedy: str
    """建议补救措施，如 '重新抓取 apple.com/iphone/pricing 页面，检查地区差异'。"""

    target_scout_index: int | None = None
    """指定由哪个 Scout 补采。None 表示由 PI 分配。"""


@dataclass
class Rebuttal:
    """Data Scout 定向补采后的回应。

    必须附带 new_data（补采的原始数据），不是纯文字辩解。
    回应必须 address 对应的 challenge_id。
    """

    rebuttal_id: str
    challenge_id: str
    """对应哪条 Challenge。"""

    new_data: list[dict[str, Any]]
    """补采的新数据，结构同 scout_results 元素。

    示例: [{"source": "apple.com/iphone/pricing", "url": "...",
            "data": {"price": "$6999", "region": "US", "timestamp": "2026-05-14"}}]
    """

    addresses_concern: bool
    """是否解决了质疑的核心关注点。False 表示尝试了但数据无法获取。"""

    note: str = ""
    """补充说明，如 '数据源仅限 US 区域，其他区域价格可能不同'。"""

    methods: list[str] = field(default_factory=list)
    """补采使用的方法列表，如 ['web_fetch', 'python_pandas_cleaning']。"""


@dataclass
class Ruling:
    """Meta-Judge 独立裁决书。

    裁决必须基于计算工具输出（统计检验/交叉验证），
    不基于身份、多数意见或 AI 判断偏好。
    """

    ruling_id: str
    resolved: list[str] = field(default_factory=list)
    """已解决的 challenge_id 列表。"""
    unresolved: list[dict[str, Any]] = field(default_factory=list)
    """无法解决的遗留问题，每条含 challenge_id/issue/reason。"""
    dismissed: list[str] = field(default_factory=list)
    """被驳回的 challenge_id 列表（质疑本身证据不足）。"""

    quality_score: float = 0.0
    """研究质量评分 0.0-1.0，基于计算而非主观：
    - 数据覆盖率: verified_data_points / expected_data_points
    - 来源交叉验证率: 被至少2个独立来源确认的数据点比例
    - 统计检验: p-value < 0.05 的数据冲突占比
    """

    computation_summary: str = ""
    """裁决依赖的计算工具输出摘要（统计检验结果、交叉验证矩阵等）。"""

    def all_challenges_resolved(self) -> bool:
        return len(self.unresolved) == 0
