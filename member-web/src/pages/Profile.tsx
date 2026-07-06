import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Dialog,
  Form,
  Input,
  List,
  Space,
  Tag,
  Toast,
} from "antd-mobile";
import { useTranslation } from "react-i18next";

import { getMyMember, updateMyMember, type MemberProfile } from "../api/member";
import { getMyBills, type Bill } from "../api/finance";
import {
  getUnreadCount,
  listMyMessages,
  localizedNotification,
  readAllMessages,
  readMessage,
  type Notification,
} from "../api/message";
import { useAuth } from "../auth/AuthContext";

export default function Profile() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState<MemberProfile | null>(null);
  const [bills, setBills] = useState<Bill[]>([]);
  const [messages, setMessages] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [noProfile, setNoProfile] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    getMyMember()
      .then((p) => {
        setProfile(p);
        setNoProfile(false);
      })
      .catch((e) => {
        if (e?.response?.status === 404) setNoProfile(true);
      });
  };

  const loadMessages = () => {
    listMyMessages()
      .then(setMessages)
      .catch(() => {});
    getUnreadCount()
      .then(setUnreadCount)
      .catch(() => {});
  };

  useEffect(() => {
    load();
    getMyBills()
      .then(setBills)
      .catch(() => {});
    loadMessages();
  }, []);

  const onReadMessage = async (id: number) => {
    await readMessage(id);
    loadMessages();
  };

  const onReadAllMessages = async () => {
    await readAllMessages();
    loadMessages();
  };

  const onSave = async () => {
    const values = await form.validateFields();
    try {
      const updated = await updateMyMember(values);
      setProfile(updated);
      setEditing(false);
      Toast.show({ content: t("profile.saved") });
    } catch {
      Toast.show({ content: t("profile.saveFailed") });
    }
  };

  return (
    <Space direction="vertical" block>
      <Card title={t("profile.account")}>
        <List>
          <List.Item extra={user?.full_name || "-"}>{t("profile.fullName")}</List.Item>
          <List.Item extra={user?.username}>{t("profile.username")}</List.Item>
          <List.Item extra={user ? t(`role.${user.role}`) : "-"}>
            {t("profile.role")}
          </List.Item>
        </List>
      </Card>

      {noProfile && (
        <Card>
          <div style={{ color: "#999" }}>{t("profile.noProfile")}</div>
        </Card>
      )}

      {profile && (
        <Card
          title={t("profile.memberCard")}
          extra={
            <Button
              size="mini"
              onClick={() => {
                form.setFieldsValue({
                  english_name: profile.english_name,
                  golf_age: profile.golf_age,
                  club_number: profile.club_number,
                });
                setEditing(true);
              }}
            >
              {t("profile.edit")}
            </Button>
          }
        >
          <List>
            <List.Item extra={profile.chinese_name}>
              {t("profile.chineseName")}
            </List.Item>
            <List.Item extra={profile.english_name || "-"}>
              {t("profile.englishName")}
            </List.Item>
            <List.Item extra={profile.golf_age ?? "-"}>
              {t("profile.golfAge")}
            </List.Item>
            <List.Item extra={profile.club_number || "-"}>
              {t("profile.clubNumber")}
            </List.Item>
            <List.Item extra={profile.handicap ?? "-"}>
              {t("profile.handicap")}
            </List.Item>
            <List.Item
              extra={<Tag color="primary">{t(`level.${profile.level}`)}</Tag>}
            >
              {t("profile.level")}
            </List.Item>
            <List.Item
              extra={<Tag>{t(`memberStatus.${profile.status}`)}</Tag>}
            >
              {t("profile.memberStatus")}
            </List.Item>
            <List.Item extra={profile.join_date || "-"}>
              {t("profile.joinDate")}
            </List.Item>
          </List>

          <div style={{ padding: "8px 12px", color: "#999", fontSize: 12 }}>
            {t("profile.privateInfo")}
          </div>
          <List>
            <List.Item extra={profile.nz_address || "-"}>
              {t("profile.address")}
            </List.Item>
            <List.Item extra={profile.local_phone || "-"}>
              {t("profile.phone")}
            </List.Item>
            <List.Item extra={profile.passport_no || "-"}>
              {t("profile.passport")}
            </List.Item>
          </List>
        </Card>
      )}

      <Card title={t("bills.title")}>
        {bills.length === 0 ? (
          <div style={{ color: "#999", padding: 8 }}>{t("bills.empty")}</div>
        ) : (
          <List>
            {bills.map((b) => (
              <List.Item
                key={b.id}
                description={t(`bills.cat.${b.category}`, b.category)}
                extra={
                  <Space direction="vertical" align="end">
                    <span>
                      {b.currency} {b.amount}
                    </span>
                    <Tag
                      color={
                        b.status === "voided"
                          ? "default"
                          : b.status === "refunded"
                            ? "warning"
                            : b.is_paid
                              ? "success"
                              : "danger"
                      }
                    >
                      {b.status === "voided"
                        ? t("bills.status.voided")
                        : b.status === "refunded"
                          ? t("bills.status.refunded")
                          : b.is_paid
                            ? t("bills.status.paid")
                            : t("bills.status.unpaid")}
                    </Tag>
                  </Space>
                }
              >
                {b.title}
              </List.Item>
            ))}
          </List>
        )}
      </Card>

      <Card
        title={
          <Space>
            <span>{t("messages.title")}</span>
            {unreadCount > 0 && <Tag color="danger">{unreadCount}</Tag>}
          </Space>
        }
        extra={
          unreadCount > 0 ? (
            <Button size="mini" onClick={onReadAllMessages}>
              {t("messages.readAll")}
            </Button>
          ) : undefined
        }
      >
        {messages.length === 0 ? (
          <div style={{ color: "#999", padding: 8 }}>{t("messages.empty")}</div>
        ) : (
          <List>
            {messages.map((m) => {
              const loc = localizedNotification(m, i18n.language);
              return (
                <List.Item
                  key={m.id}
                  description={loc.body}
                  extra={
                    !m.is_read ? (
                      <Button size="mini" onClick={() => onReadMessage(m.id)}>
                        {t("messages.markRead")}
                      </Button>
                    ) : (
                      <Tag>{t("messages.read")}</Tag>
                    )
                  }
                >
                  {loc.title}
                </List.Item>
              );
            })}
          </List>
        )}
      </Card>

      <div style={{ padding: 12 }}>
        <Button block color="danger" fill="outline" onClick={logout}>
          {t("profile.logout")}
        </Button>
      </div>

      <Dialog
        visible={editing}
        title={t("profile.edit")}
        content={
          <Form form={form} layout="horizontal">
            <Form.Item name="english_name" label={t("profile.englishName")}>
              <Input />
            </Form.Item>
            <Form.Item name="golf_age" label={t("profile.golfAge")}>
              <Input type="number" />
            </Form.Item>
            <Form.Item name="club_number" label={t("profile.clubNumber")}>
              <Input />
            </Form.Item>
          </Form>
        }
        actions={[
          [
            { key: "cancel", text: t("profile.cancel"), onClick: () => setEditing(false) },
            { key: "save", text: t("profile.save"), bold: true, onClick: onSave },
          ],
        ]}
      />
    </Space>
  );
}
