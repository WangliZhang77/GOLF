"""赛事分组算法：确定性、无优化器的简单规则引擎。

规则：
1. 按差点升序排序（差点缺失排最后），同差点按 member_id 保证结果可复现。
2. 均匀切块：组数 = ceil(n / group_size)，各组人数相差不超过 1。
3. 有限轮次（至多 3 轮）相邻组换人，尽量避免同一球队全部扎堆在一组；
   仅在相邻组之间寻找差点最接近的可换对象，不做全局最优搜索。
4. 组内按差点升序排列 order_number。

不考虑性别（Member 模型无性别字段，本轮范围已与用户确认）。
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math

_UNKNOWN_HANDICAP = Decimal("999.9")


@dataclass
class GroupingPlayer:
    member_id: int
    handicap: Decimal | None
    team_id: int | None
    registration_id: int | None = None


def _sort_key(p: GroupingPlayer):
    return (p.handicap if p.handicap is not None else _UNKNOWN_HANDICAP, p.member_id)


def generate_groups(
    players: list[GroupingPlayer], group_size: int = 4
) -> list[list[GroupingPlayer]]:
    if not players:
        return []

    ordered = sorted(players, key=_sort_key)

    n = len(ordered)
    k = math.ceil(n / group_size)
    base, remainder = divmod(n, k)
    sizes = [base + 1] * remainder + [base] * (k - remainder)

    groups: list[list[GroupingPlayer]] = []
    idx = 0
    for size in sizes:
        groups.append(ordered[idx : idx + size])
        idx += size

    for _ in range(3):
        changed = False
        for gi, group in enumerate(groups):
            team_counts: dict[int, int] = {}
            for p in group:
                if p.team_id is not None:
                    team_counts[p.team_id] = team_counts.get(p.team_id, 0) + 1
            dup_team_ids = [tid for tid, c in team_counts.items() if c > 1]

            for tid in dup_team_ids:
                dup_players = [p for p in group if p.team_id == tid][1:]
                for dup in dup_players:
                    best: tuple[GroupingPlayer, int, Decimal] | None = None
                    for nj in (gi - 1, gi + 1):
                        if not (0 <= nj < len(groups)):
                            continue
                        origin_team_ids = {
                            p.team_id for p in groups[gi] if p.member_id != dup.member_id
                        }
                        for other in groups[nj]:
                            if other.team_id == tid:
                                continue
                            if other.team_id is not None and other.team_id in origin_team_ids:
                                continue
                            diff = abs(
                                (other.handicap if other.handicap is not None else _UNKNOWN_HANDICAP)
                                - (dup.handicap if dup.handicap is not None else _UNKNOWN_HANDICAP)
                            )
                            if best is None or diff < best[2]:
                                best = (other, nj, diff)
                    if best:
                        other, nj, _ = best
                        groups[gi].remove(dup)
                        groups[nj].remove(other)
                        groups[gi].append(other)
                        groups[nj].append(dup)
                        changed = True
        if not changed:
            break

    for group in groups:
        group.sort(key=_sort_key)

    return groups
