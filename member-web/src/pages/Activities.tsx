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

import {
  checkinActivity,
  listActivities,
  parseCheckinQr,
  registerActivity,
  type Activity,
  type ActivityType,
} from "../api/activity";

export default function Activities() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Activity[]>([]);
  const [checkinOpen, setCheckinOpen] = useState(false);
  const [checkinInput, setCheckinInput] = useState("");
  const [familyOpen, setFamilyOpen] = useState(false);
  const [registerId, setRegisterId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const load = () =>
    listActivities()
      .then(setRows)
      .catch(() => Toast.show({ content: t("activity.loadFailed") }));

  useEffect(() => {
    load();
  }, []);

  const onRegister = async (id: number, withFamily: boolean) => {
    if (withFamily) {
      setRegisterId(id);
      setFamilyOpen(true);
      return;
    }
    try {
      await registerActivity(id);
      Toast.show({ content: t("activity.registerOk") });
      load();
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || t("activity.registerFailed");
      Toast.show({ content: String(msg) });
    }
  };

  const submitFamilyRegister = async () => {
    if (registerId == null) return;
    const names = (form.getFieldValue("family_names") as string) || "";
    const companions = names
      .split(/[,，\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((name) => ({ name }));
    try {
      await registerActivity(registerId, companions);
      Toast.show({ content: t("activity.registerOk") });
      setFamilyOpen(false);
      form.resetFields();
      load();
    } catch {
      Toast.show({ content: t("activity.registerFailed") });
    }
  };

  const onCheckin = async () => {
    const parsed = parseCheckinQr(checkinInput);
    if (!parsed) {
      Toast.show({ content: t("activity.invalidQr") });
      return;
    }
    try {
      await checkinActivity(parsed.id, parsed.token);
      Toast.show({ content: t("activity.checkinOk") });
      setCheckinOpen(false);
      setCheckinInput("");
      load();
    } catch {
      Toast.show({ content: t("activity.checkinFailed") });
    }
  };

  return (
    <Space direction="vertical" block>
      <Button block color="primary" onClick={() => setCheckinOpen(true)}>
        {t("activity.scanCheckin")}
      </Button>

      <List header={t("activity.listTitle")}>
        {rows.map((a) => (
          <List.Item
            key={a.id}
            description={
              <Space direction="vertical">
                <span>
                  {t(`activityType.${a.activity_type as ActivityType}`)} ·{" "}
                  {new Date(a.start_at).toLocaleString()}
                </span>
                {a.course_name && <span>{a.course_name}</span>}
                <Tag color="primary">
                  {t("activity.slots")}: {a.member_registered_count ?? 0}/
                  {a.max_participants}
                </Tag>
              </Space>
            }
            extra={
              <Space direction="vertical">
                <Button
                  size="mini"
                  color="primary"
                  disabled={a.course_slots_locked}
                  onClick={() => onRegister(a.id, false)}
                >
                  {t("activity.register")}
                </Button>
                {a.family_allowed && (
                  <Button
                    size="mini"
                    onClick={() => onRegister(a.id, true)}
                    disabled={a.course_slots_locked}
                  >
                    {t("activity.registerWithFamily")}
                  </Button>
                )}
              </Space>
            }
          >
            {a.title}
          </List.Item>
        ))}
        {rows.length === 0 && (
          <Card>
            <div style={{ color: "#999", padding: 12 }}>{t("activity.empty")}</div>
          </Card>
        )}
      </List>

      <Dialog
        visible={checkinOpen}
        title={t("activity.scanCheckin")}
        content={
          <Input
            placeholder={t("activity.checkinPlaceholder")}
            value={checkinInput}
            onChange={setCheckinInput}
          />
        }
        actions={[
          [
            {
              key: "cancel",
              text: t("activity.cancel"),
              onClick: () => setCheckinOpen(false),
            },
            { key: "ok", text: t("activity.confirm"), bold: true, onClick: onCheckin },
          ],
        ]}
      />

      <Dialog
        visible={familyOpen}
        title={t("activity.familyTitle")}
        content={
          <Form form={form}>
            <Form.Item name="family_names" label={t("activity.familyNames")}>
              <Input placeholder={t("activity.familyPlaceholder")} />
            </Form.Item>
          </Form>
        }
        actions={[
          [
            {
              key: "cancel",
              text: t("activity.cancel"),
              onClick: () => setFamilyOpen(false),
            },
            {
              key: "ok",
              text: t("activity.confirm"),
              bold: true,
              onClick: submitFamilyRegister,
            },
          ],
        ]}
      />
    </Space>
  );
}
