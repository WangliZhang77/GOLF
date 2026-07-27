import { useEffect, useState } from "react";
import { List, NavBar, Space, Tabs, Tag } from "antd-mobile";
import { useTranslation } from "react-i18next";

import { listRankings, type Ranking } from "../api/ranking";
import { getMyMember } from "../api/member";

export default function CompetitionRanking({
  competitionId,
  onBack,
}: {
  competitionId: number;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  const [individual, setIndividual] = useState<Ranking[]>([]);
  const [team, setTeam] = useState<Ranking[]>([]);
  const [myMemberId, setMyMemberId] = useState<number | null>(null);
  const [myTeamId, setMyTeamId] = useState<number | null>(null);

  useEffect(() => {
    listRankings(competitionId, "individual").then(setIndividual).catch(() => {});
    listRankings(competitionId, "team").then(setTeam).catch(() => {});
    getMyMember()
      .then((m) => {
        setMyMemberId(m.id);
        setMyTeamId(m.team_id);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [competitionId]);

  return (
    <Space direction="vertical" block>
      <NavBar onBack={onBack}>{t("ranking.title")}</NavBar>
      <Tabs>
        <Tabs.Tab title={t("rankingScope.individual")} key="individual">
          <List>
            {individual.map((r) => (
              <List.Item
                key={r.id}
                extra={
                  r.award ? <Tag color="warning">{t(`award.${r.award}`)}</Tag> : r.score
                }
              >
                <span style={{ fontWeight: r.member_id === myMemberId ? 700 : 400 }}>
                  #{r.rank} · {t("competition.memberId")} {r.member_id}
                  {r.member_id === myMemberId ? ` (${t("ranking.you")})` : ""}
                </span>
              </List.Item>
            ))}
            {individual.length === 0 && (
              <List.Item>{t("ranking.notPublished")}</List.Item>
            )}
          </List>
        </Tabs.Tab>
        <Tabs.Tab title={t("rankingScope.team")} key="team">
          <List>
            {team.map((r) => (
              <List.Item
                key={r.id}
                extra={
                  r.award ? <Tag color="warning">{t(`award.${r.award}`)}</Tag> : r.score
                }
              >
                <span style={{ fontWeight: r.team_id === myTeamId ? 700 : 400 }}>
                  #{r.rank} · {t("ranking.team")} {r.team_id}
                  {r.team_id === myTeamId ? ` (${t("ranking.yourTeam")})` : ""}
                </span>
              </List.Item>
            ))}
            {team.length === 0 && <List.Item>{t("ranking.notPublished")}</List.Item>}
          </List>
        </Tabs.Tab>
      </Tabs>
    </Space>
  );
}
