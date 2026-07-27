import { useEffect, useState } from "react";
import { Card, List, Space, Tag } from "antd-mobile";
import { useTranslation } from "react-i18next";

import { getMyBills, type Bill } from "../api/finance";
import { getMyHandicap, type HandicapDashboard } from "../api/handicap";
import { getMyMember, type MemberProfile } from "../api/member";
import { listTeams, type Team } from "../api/org";
import { listCompetitions, type Competition } from "../api/competition";

export default function Home() {
  const { t } = useTranslation();
  const [profile, setProfile] = useState<MemberProfile | null>(null);
  const [handicap, setHandicap] = useState<HandicapDashboard | null>(null);
  const [bills, setBills] = useState<Bill[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [competitions, setCompetitions] = useState<Competition[]>([]);

  useEffect(() => {
    getMyMember()
      .then(setProfile)
      .catch(() => {});
    getMyHandicap()
      .then(setHandicap)
      .catch(() => {});
    getMyBills()
      .then(setBills)
      .catch(() => {});
    listTeams()
      .then(setTeams)
      .catch(() => {});
    listCompetitions()
      .then(setCompetitions)
      .catch(() => {});
  }, []);

  const teamName = profile?.team_id
    ? teams.find((tm) => tm.id === profile.team_id)?.name ?? null
    : null;

  const outstandingBills = bills.filter((b) => !b.is_paid && b.status === "confirmed");
  const outstandingAmount = outstandingBills.reduce((sum, b) => sum + Number(b.amount), 0);

  const registered = competitions.filter((c) => c.my_registration_status);
  const now = Date.now();
  const past = registered
    .filter((c) => new Date(c.start_time).getTime() <= now)
    .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime());
  const upcoming = registered
    .filter((c) => new Date(c.start_time).getTime() > now)
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
  const recentCompetition = past[0] ?? upcoming[0] ?? null;

  return (
    <Space direction="vertical" block>
      {profile && (
        <Card title={t("home.myProfile")}>
          <List>
            <List.Item extra={profile.chinese_name}>{t("home.name")}</List.Item>
            <List.Item extra={<Tag color="primary">{t(`level.${profile.level}`)}</Tag>}>
              {t("home.level")}
            </List.Item>
            <List.Item extra={teamName ?? t("home.noTeam")}>{t("home.myTeam")}</List.Item>
          </List>
        </Card>
      )}

      {handicap && (
        <Card title={t("home.myHandicap")}>
          <Space align="center">
            <span style={{ fontSize: 24, fontWeight: 700 }}>
              {handicap.current_handicap ?? "-"}
            </span>
            <Tag
              color={
                handicap.trend === "declining"
                  ? "success"
                  : handicap.trend === "rising"
                    ? "warning"
                    : "default"
              }
            >
              {t(`handicapTrend.${handicap.trend}`)}
            </Tag>
          </Space>
        </Card>
      )}

      <Card title={t("home.recentCompetition")}>
        {recentCompetition ? (
          <List>
            <List.Item
              extra={
                <Tag color="primary">
                  {t(`competitionStatus.${recentCompetition.status}`)}
                </Tag>
              }
              description={new Date(recentCompetition.start_time).toLocaleDateString()}
            >
              {recentCompetition.name}
            </List.Item>
          </List>
        ) : (
          <div style={{ color: "#999", padding: 8 }}>{t("home.noCompetition")}</div>
        )}
      </Card>

      <Card title={t("home.duesStatus")}>
        {outstandingBills.length === 0 ? (
          <Tag color="success">{t("home.noDues")}</Tag>
        ) : (
          <Space direction="vertical">
            <Tag color="danger">
              {t("home.duesOutstanding", { count: outstandingBills.length })}
            </Tag>
            <span>
              {t("home.duesAmount")}: {outstandingAmount.toFixed(2)}
            </span>
          </Space>
        )}
      </Card>
    </Space>
  );
}
