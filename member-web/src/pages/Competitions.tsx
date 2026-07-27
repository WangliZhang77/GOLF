import { useEffect, useState } from "react";
import { Button, Card, Dialog, List, Space, Tag, Toast } from "antd-mobile";
import { useTranslation } from "react-i18next";

import {
  listCompetitions,
  registerCompetition,
  type Competition,
  type CompetitionType,
} from "../api/competition";
import { getMyGroup, type CompetitionGroup } from "../api/grouping";
import CompetitionRanking from "./CompetitionRanking";
import ScoreEntry from "./ScoreEntry";

export default function Competitions() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Competition[]>([]);
  const [groupOpen, setGroupOpen] = useState(false);
  const [group, setGroup] = useState<CompetitionGroup | null>(null);
  const [scoringId, setScoringId] = useState<number | null>(null);
  const [rankingId, setRankingId] = useState<number | null>(null);

  const load = () =>
    listCompetitions()
      .then(setRows)
      .catch(() => Toast.show({ content: t("competition.loadFailed") }));

  useEffect(() => {
    load();
  }, []);

  const isDeadlinePassed = (c: Competition) =>
    !!c.registration_deadline && new Date(c.registration_deadline) < new Date();

  const onRegister = async (id: number) => {
    try {
      await registerCompetition(id);
      Toast.show({ content: t("competition.registerOk") });
      load();
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || t("competition.registerFailed");
      Toast.show({ content: String(msg) });
    }
  };

  const onViewGroup = async (id: number) => {
    try {
      const g = await getMyGroup(id);
      setGroup(g);
      setGroupOpen(true);
    } catch {
      Toast.show({ content: t("grouping.notGrouped") });
    }
  };

  if (scoringId !== null) {
    return <ScoreEntry competitionId={scoringId} onBack={() => setScoringId(null)} />;
  }
  if (rankingId !== null) {
    return <CompetitionRanking competitionId={rankingId} onBack={() => setRankingId(null)} />;
  }

  return (
    <Space direction="vertical" block>
      <List header={t("competition.listTitle")}>
        {rows.map((c) => {
          const canRegister =
            c.status === "open" &&
            !isDeadlinePassed(c) &&
            !c.my_registration_status;
          return (
            <List.Item
              key={c.id}
              description={
                <Space direction="vertical">
                  <span>
                    {t(`competitionType.${c.competition_type as CompetitionType}`)}
                    {c.level ? ` · ${c.level}` : ""} ·{" "}
                    {new Date(c.start_time).toLocaleString()}
                  </span>
                  {c.fee && (
                    <span>
                      {t("competition.fee")}: {c.fee}
                    </span>
                  )}
                  {c.max_handicap && (
                    <span>
                      {t("competition.maxHandicap")}: {c.max_handicap}
                    </span>
                  )}
                  <Tag color="primary">
                    {t("competition.registered")}: {c.registered_count ?? 0}/
                    {c.max_players}
                  </Tag>
                </Space>
              }
              extra={
                c.my_registration_status ? (
                  <Space direction="vertical">
                    <Tag color={c.my_registration_status === "rejected" ? "danger" : "success"}>
                      {t(`competitionApprovalStatus.${c.my_registration_status}`)}
                    </Tag>
                    {c.my_registration_status === "approved" && (
                      <Button size="mini" onClick={() => onViewGroup(c.id)}>
                        {t("grouping.myGroup")}
                      </Button>
                    )}
                    {c.my_registration_status === "approved" &&
                      (c.status === "playing" || c.status === "review") && (
                        <Button size="mini" color="primary" onClick={() => setScoringId(c.id)}>
                          {t("scoring.title")}
                        </Button>
                      )}
                    {c.status === "completed" && (
                      <Button size="mini" onClick={() => setRankingId(c.id)}>
                        {t("ranking.title")}
                      </Button>
                    )}
                  </Space>
                ) : (
                  <Button
                    size="mini"
                    color="primary"
                    disabled={!canRegister}
                    onClick={() => onRegister(c.id)}
                  >
                    {t("competition.register")}
                  </Button>
                )
              }
            >
              {c.name}
            </List.Item>
          );
        })}
        {rows.length === 0 && (
          <Card>
            <div style={{ color: "#999", padding: 12 }}>{t("competition.empty")}</div>
          </Card>
        )}
      </List>

      <Dialog
        visible={groupOpen}
        title={group ? `${t("grouping.group")} ${group.group_number}` : t("grouping.myGroup")}
        content={
          group && (
            <Space direction="vertical">
              {group.tee_time && (
                <span>
                  {t("grouping.teeTime")}: {new Date(group.tee_time).toLocaleString()}
                </span>
              )}
              <span>
                {t("grouping.startingHole")}: {group.starting_hole}
              </span>
              <List>
                {group.players.map((p) => (
                  <List.Item key={p.id}>
                    #{p.order_number} · {t("competition.memberId")} {p.member_id}
                    {p.handicap ? ` · HC ${p.handicap}` : ""}
                  </List.Item>
                ))}
              </List>
            </Space>
          )
        }
        closeOnAction
        actions={[
          [{ key: "close", text: t("activity.confirm"), onClick: () => setGroupOpen(false) }],
        ]}
      />
    </Space>
  );
}
