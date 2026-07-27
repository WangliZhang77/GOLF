import { useEffect, useState } from "react";
import { Card, Col, Row, Space, Statistic, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";

import { fetchWelcome } from "../api/client";
import { getAnalyticsDashboard, type AnalyticsDashboard } from "../api/analytics";

const { Title, Paragraph, Text } = Typography;

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");
  const [message, setMessage] = useState<string>("");
  const [analytics, setAnalytics] = useState<AnalyticsDashboard | null>(null);

  const load = () => {
    setStatus("checking");
    fetchWelcome()
      .then((data) => {
        setStatus("ok");
        setMessage(data.message);
      })
      .catch(() => setStatus("error"));
  };

  const loadAnalytics = () => {
    getAnalyticsDashboard()
      .then(setAnalytics)
      .catch(() => setAnalytics(null));
  };

  useEffect(() => {
    load();
    loadAnalytics();
    // 语言变化后重新请求，验证双语联动
  }, [i18n.language]);

  const statusTag = {
    checking: <Tag color="processing">{t("dashboard.checking")}</Tag>,
    ok: <Tag color="success">{t("dashboard.connected")}</Tag>,
    error: <Tag color="error">{t("dashboard.failed")}</Tag>,
  }[status];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <Title level={3} style={{ marginBottom: 4 }}>
          {t("dashboard.welcome")}
        </Title>
        <Paragraph type="secondary">{t("dashboard.subtitle")}</Paragraph>
      </div>

      {analytics && (
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <Card title={t("dashboard.sections.members")} size="small">
            <Row gutter={16}>
              <Col span={5}>
                <Statistic
                  title={t("dashboard.stats.members")}
                  value={analytics.members.total}
                />
              </Col>
              <Col span={5}>
                <Statistic
                  title={t("dashboard.stats.newLast30d")}
                  value={analytics.members.new_last_30d}
                />
              </Col>
              <Col span={5}>
                <Statistic
                  title={t("dashboard.stats.activeMembers")}
                  value={analytics.members.active}
                />
              </Col>
              <Col span={5}>
                <Statistic
                  title={t("dashboard.stats.sleepingMembers")}
                  value={analytics.members.sleeping}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title={t("dashboard.stats.teamCount")}
                  value={analytics.members.team_count}
                />
              </Col>
            </Row>
          </Card>

          <Card title={t("dashboard.sections.activities")} size="small">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title={t("dashboard.stats.activities")}
                  value={analytics.activities.total}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={t("dashboard.stats.avgParticipants")}
                  value={analytics.activities.avg_participants}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t("dashboard.stats.mostAttended")}
                  value={
                    analytics.activities.most_attended
                      ? `${analytics.activities.most_attended.title} (${analytics.activities.most_attended.count})`
                      : "-"
                  }
                />
              </Col>
            </Row>
          </Card>

          <Card title={t("dashboard.sections.competitions")} size="small">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title={t("dashboard.stats.competitions")}
                  value={analytics.competitions.total}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={t("dashboard.stats.totalParticipants")}
                  value={analytics.competitions.total_participants}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={t("dashboard.stats.avgNetScore")}
                  value={analytics.competitions.avg_net_score ?? "-"}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={t("dashboard.stats.handicapChange")}
                  value={analytics.competitions.handicap_change ?? "-"}
                />
              </Col>
            </Row>
          </Card>

          <Card title={t("dashboard.sections.finance")} size="small">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title={t("dashboard.stats.income")} value={analytics.finance.income} />
              </Col>
              <Col span={6}>
                <Statistic
                  title={t("dashboard.stats.expense")}
                  value={analytics.finance.expense}
                />
              </Col>
              <Col span={6}>
                <Statistic title={t("dashboard.stats.profit")} value={analytics.finance.profit} />
              </Col>
              <Col span={6}>
                <Statistic
                  title={t("dashboard.stats.sponsorshipTotal")}
                  value={analytics.finance.sponsorship_total}
                />
              </Col>
            </Row>
          </Card>
        </Space>
      )}

      <Card title={t("dashboard.backendStatus")}>
        <Space direction="vertical">
          <Space>
            <Text strong>{t("dashboard.backendStatus")}:</Text>
            {statusTag}
          </Space>
          <Space>
            <Text strong>{t("dashboard.backendMessage")}:</Text>
            <Text>{message || "-"}</Text>
          </Space>
        </Space>
      </Card>
    </Space>
  );
}
