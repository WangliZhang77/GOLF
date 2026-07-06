import { useEffect, useState } from "react";
import { Card, Col, Row, Space, Statistic, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";

import { fetchWelcome } from "../api/client";
import { listMembers } from "../api/member";
import { listActivities } from "../api/activity";
import { getSummary } from "../api/finance";
import { listMyMessages } from "../api/message";

const { Title, Paragraph, Text } = Typography;

interface Stats {
  members: number;
  activities: number;
  unreconciled: number;
  unread: number;
}

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");
  const [message, setMessage] = useState<string>("");
  const [stats, setStats] = useState<Stats | null>(null);

  const load = () => {
    setStatus("checking");
    fetchWelcome()
      .then((data) => {
        setStatus("ok");
        setMessage(data.message);
      })
      .catch(() => setStatus("error"));
  };

  const loadStats = async () => {
    const [members, activities, summary, messages] = await Promise.all([
      listMembers().catch(() => []),
      listActivities().catch(() => []),
      getSummary().catch(() => null),
      listMyMessages(true).catch(() => []),
    ]);
    setStats({
      members: members.length,
      activities: activities.length,
      unreconciled: summary?.unreconciled_count ?? 0,
      unread: messages.length,
    });
  };

  useEffect(() => {
    load();
    loadStats();
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

      {stats && (
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic title={t("dashboard.stats.members")} value={stats.members} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t("dashboard.stats.activities")}
                value={stats.activities}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t("dashboard.stats.unreconciled")}
                value={stats.unreconciled}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title={t("dashboard.stats.unread")} value={stats.unread} />
            </Card>
          </Col>
        </Row>
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
