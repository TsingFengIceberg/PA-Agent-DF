"""Collaboration SubGraph 构建模块。

两个独立编译的 SubGraph：
- ResearchSubGraph: PI → Scouts(Send) → Critic ⇄ Scouts → Meta-Judge → PI Review
- AnalysisSubGraph: Analyst Lead → Synthesizer → Internal Reviewer
"""
