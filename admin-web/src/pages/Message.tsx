import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Form,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  message,
} from "antd";
import { useTranslation } from "react-i18next";

import { listActivities, type Activity } from "../api/activity";
import {
  listMyMessages,
  listSentMessages,
  localizedNotification,
  readAllMessages,
  readMessage,
  sendActivityReminder,
  sendDuesReminder,
  type Notification,
} from "../api/message";
import { listMembers, type Member } from "../api/member";
import { useAuth } from "../auth/AuthContext";

export default function MessagePage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [inbox, setInbox] = useState<Notification[]>([]);
  const [sent, setSent] = useState<Notification[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [memberId, setMemberId] = useState<number | undefined>();
  const [activityId, setActivityId] = useState<number | undefined>();
  const [allOutstanding, setAllOutstanding] = useState(false);

  const loadInbox = () =>
    listMyMessages()
      .then(setInbox)
      .catch(() => message.error(t("message.opFailed")));

  const loadSent = () =>
    listSentMessages()
      .then(setSent)
      .catch(() => {});

  useEffect(() => {
    loadInbox();
    loadSent();
    listMembers()
      .then(setMembers)
      .catch(() => {});
    listActivities()
      .then(setActivities)
      .catch(() => {});
  }, []);

  const onDues = async () => {
    try {
      const res = await sendDuesReminder(
        allOutstanding ? { all_outstanding: true } : { member_id: memberId }
      );
      message.success(`${t("message.duesSent")}: ${res.sent_count}`);
      loadSent();
    } catch {
      message.error(t("message.opFailed"));
    }
  };

  const onActivityReminder = async () => {
    if (!activityId) return;
    try {
      const res = await sendActivityReminder(activityId);
      message.success(`${t("message.activitySent")}: ${res.sent_count}`);
      loadSent();
    } catch {
      message.error(t("message.opFailed"));
    }
  };

  const onRead = async (id: number) => {
    await readMessage(id);
    loadInbox();
  };

  const onReadAll = async () => {
    await readAllMessages();
    loadInbox();
  };

  const canSendDues =
    user?.role === "super_admin" || user?.role === "finance";

  const inboxColumns = [
    {
      title: t("message.type"),
      dataIndex: "message_type",
      render: (v: string) => t(`message.types.${v}`),
    },
    {
      title: t("message.title"),
      key: "title",
      render: (_: unknown, r: Notification) =>
        localizedNotification(r, i18n.language).title,
    },
    {
      title: t("message.body"),
      key: "body",
      ellipsis: true,
      render: (_: unknown, r: Notification) =>
        localizedNotification(r, i18n.language).body,
    },
    {
      title: t("message.read"),
      dataIndex: "is_read",
      render: (v: boolean) =>
        v ? <Tag color="default">{t("message.readYes")}</Tag> : (
          <Tag color="blue">{t("message.readNo")}</Tag>
        ),
    },
    {
      title: t("message.actions"),
      key: "actions",
      render: (_: unknown, r: Notification) =>
        !r.is_read ? (
          <Button size="small" onClick={() => onRead(r.id)}>
            {t("message.markRead")}
          </Button>
        ) : null,
    },
  ];

  const sentColumns = [
    {
      title: t("message.type"),
      dataIndex: "message_type",
      render: (v: string) => t(`message.types.${v}`),
    },
    {
      title: t("message.title"),
      key: "title",
      render: (_: unknown, r: Notification) =>
        localizedNotification(r, i18n.language).title,
    },
    {
      title: t("message.createdAt"),
      dataIndex: "created_at",
      render: (v: string) => new Date(v).toLocaleString(),
    },
  ];

  return (
    <Tabs
      items={[
        {
          key: "inbox",
          label: t("message.tabInbox"),
          children: (
            <Space direction="vertical" style={{ width: "100%" }} size="large">
              <Button onClick={onReadAll}>{t("message.readAll")}</Button>
              <Table rowKey="id" dataSource={inbox} columns={inboxColumns} pagination={{ pageSize: 10 }} />
            </Space>
          ),
        },
        ...(canSendDues
          ? [
              {
                key: "dues",
                label: t("message.tabDues"),
                children: (
                  <Card title={t("message.tabDues")}>
                    <Form layout="vertical">
                      <Form.Item label={t("message.batchOutstanding")}>
                        <Switch checked={allOutstanding} onChange={setAllOutstanding} />
                      </Form.Item>
                      {!allOutstanding && (
                        <Form.Item label={t("message.selectMember")}>
                          <Select
                            showSearch
                            optionFilterProp="label"
                            style={{ width: 320 }}
                            value={memberId}
                            onChange={setMemberId}
                            options={members.map((m) => ({
                              value: m.id,
                              label: `${m.chinese_name} (#${m.id})`,
                            }))}
                          />
                        </Form.Item>
                      )}
                      <Button type="primary" onClick={onDues}>
                        {t("message.sendDues")}
                      </Button>
                    </Form>
                  </Card>
                ),
              },
            ]
          : []),
        {
          key: "activity",
          label: t("message.tabActivity"),
          children: (
            <Card title={t("message.tabActivity")}>
              <Space>
                <Select
                  style={{ width: 280 }}
                  placeholder={t("message.selectActivity")}
                  value={activityId}
                  onChange={setActivityId}
                  options={activities.map((a) => ({
                    value: a.id,
                    label: a.title,
                  }))}
                />
                <Button type="primary" onClick={onActivityReminder}>
                  {t("message.sendActivity")}
                </Button>
              </Space>
            </Card>
          ),
        },
        {
          key: "sent",
          label: t("message.tabSent"),
          children: (
            <Table rowKey="id" dataSource={sent} columns={sentColumns} pagination={{ pageSize: 15 }} />
          ),
        },
      ]}
    />
  );
}
