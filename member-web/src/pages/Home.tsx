import { useEffect, useState, type CSSProperties } from "react";
import { Card, Grid, List, Space, Tag } from "antd-mobile";
import {
  BillOutline,
  FlagOutline,
  HistogramOutline,
  TeamOutline,
  UserOutline,
} from "antd-mobile-icons";
import { useTranslation } from "react-i18next";

import { getMyBills, type Bill } from "../api/finance";
import { getMyHandicap, type HandicapDashboard } from "../api/handicap";
import { getMyMember, type MemberProfile } from "../api/member";
import { listTeams, type Team } from "../api/org";
import { listCompetitions, type Competition } from "../api/competition";
import IconBadge from "../components/IconBadge";

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
  const duesClear = outstandingBills.length === 0;

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
    <Space direction="vertical" block style={{ "--gap": "12px" } as CSSProperties}>
      {profile && (
        <Card
          style={{
            background: "linear-gradient(135deg, #1f7a3d 0%, #35a35a 100%)",
            borderRadius: 16,
          }}
          bodyStyle={{ padding: 20 }}
        >
          <Space align="center">
            <IconBadge
              icon={<UserOutline />}
              size={52}
              background="rgba(255,255,255,0.25)"
              color="#fff"
            />
            <Space direction="vertical" style={{ "--gap": "2px" } as CSSProperties}>
              <span style={{ color: "#fff", fontSize: 18, fontWeight: 700 }}>
                {profile.chinese_name}
              </span>
              <Tag color="default" style={{ background: "rgba(255,255,255,0.85)" }}>
                {t(`level.${profile.level}`)}
              </Tag>
            </Space>
          </Space>
        </Card>
      )}

      <Grid columns={2} gap={12}>
        <Grid.Item>
          <Card bodyStyle={{ padding: 14 }}>
            <Space direction="vertical" style={{ "--gap": "6px" } as CSSProperties}>
              <IconBadge icon={<TeamOutline />} background="#e6f4ff" color="#1677ff" />
              <span style={{ fontSize: 12, color: "#999" }}>{t("home.myTeam")}</span>
              <span style={{ fontSize: 15, fontWeight: 600 }}>
                {teamName ?? t("home.noTeam")}
              </span>
            </Space>
          </Card>
        </Grid.Item>
        <Grid.Item>
          <Card bodyStyle={{ padding: 14 }}>
            <Space direction="vertical" style={{ "--gap": "6px" } as CSSProperties}>
              <IconBadge icon={<HistogramOutline />} background="#e8f5e9" color="#1f7a3d" />
              <span style={{ fontSize: 12, color: "#999" }}>{t("home.myHandicap")}</span>
              <span style={{ fontSize: 18, fontWeight: 700 }}>
                {handicap?.current_handicap ?? "-"}
              </span>
              {handicap && (
                <Tag
                  color={
                    handicap.trend === "declining"
                      ? "success"
                      : handicap.trend === "rising"
                        ? "warning"
                        : "default"
                  }
                  style={{ whiteSpace: "normal", wordBreak: "break-word" }}
                >
                  {t(`handicapTrend.${handicap.trend}`)}
                </Tag>
              )}
            </Space>
          </Card>
        </Grid.Item>
      </Grid>

      <Card
        title={
          <Space align="center">
            <IconBadge icon={<FlagOutline />} size={28} background="#fff7e6" color="#d48806" />
            <span>{t("home.recentCompetition")}</span>
          </Space>
        }
      >
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

      <Card
        title={
          <Space align="center">
            <IconBadge
              icon={<BillOutline />}
              size={28}
              background={duesClear ? "#e8f5e9" : "#fff1f0"}
              color={duesClear ? "#1f7a3d" : "#cf1322"}
            />
            <span>{t("home.duesStatus")}</span>
          </Space>
        }
      >
        {duesClear ? (
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
