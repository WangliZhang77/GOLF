import { useEffect, useState } from "react";
import {
  Button,
  DatePicker,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  QRCode,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from "antd";
import { useTranslation } from "react-i18next";

import {
  createActivity,
  getAttendanceStats,
  listActivities,
  listRegistrations,
  markAbsent,
  publishActivity,
  type Activity,
  type ActivityStatus,
  type ActivityType,
  type AttendanceStats,
  type Registration,
} from "../api/activity";
import { listOrganizations, type Organization } from "../api/org";

const TYPE_COLOR: Record<ActivityType, string> = {
  weekly_round: "green",
  team_building: "blue",
  course_visit: "cyan",
  networking: "purple",
  newbie_salon: "orange",
};

const STATUS_COLOR: Record<ActivityStatus, string> = {
  draft: "default",
  published: "success",
  closed: "warning",
  cancelled: "error",
};

export default function ActivityPage() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Activity[]>([]);
  const [branches, setBranches] = useState<Organization[]>([]);
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<Activity | null>(null);
  const [regs, setRegs] = useState<Registration[]>([]);
  const [stats, setStats] = useState<AttendanceStats | null>(null);
  const [form] = Form.useForm();

  const load = () => listActivities().then(setRows).catch(() => {});
  useEffect(() => {
    load();
    listOrganizations()
      .then((os) => setBranches(os.filter((o) => o.level === "branch")))
      .catch(() => {});
  }, []);

  const onCreate = async () => {
    const v = await form.validateFields();
    try {
      const created = await createActivity({
        title: v.title,
        activity_type: v.activity_type,
        branch_id: v.branch_id,
        start_at: v.start_at.toISOString(),
        description: v.description,
        course_name: v.course_name,
        max_participants: v.max_participants,
        max_family_slots: v.max_family_slots,
        family_allowed: v.family_allowed,
        course_slots_locked: v.course_slots_locked,
      });
      await publishActivity(created.id);
      message.success(t("activity.createSuccess"));
      setOpen(false);
      form.resetFields();
      load();
    } catch {
      message.error(t("activity.opFailed"));
    }
  };

  const openDetail = async (a: Activity) => {
    setDetail(a);
    try {
      const [r, s] = await Promise.all([
        listRegistrations(a.id),
        getAttendanceStats(a.id),
      ]);
      setRegs(r);
      setStats(s);
    } catch {
      message.error(t("activity.opFailed"));
    }
  };

  const onAbsent = async (regId: number) => {
    if (!detail) return;
    try {
      await markAbsent(detail.id, regId);
      openDetail(detail);
    } catch {
      message.error(t("activity.opFailed"));
    }
  };

  const branchName = (id: number) =>
    branches.find((b) => b.id === id)?.name ?? id;

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: t("activity.title"), dataIndex: "title" },
    {
      title: t("activity.type"),
      dataIndex: "activity_type",
      render: (v: ActivityType) => (
        <Tag color={TYPE_COLOR[v]}>{t(`activityType.${v}`)}</Tag>
      ),
    },
    {
      title: t("activity.status"),
      dataIndex: "status",
      render: (v: ActivityStatus) => (
        <Tag color={STATUS_COLOR[v]}>{t(`activityStatus.${v}`)}</Tag>
      ),
    },
    {
      title: t("activity.branch"),
      dataIndex: "branch_id",
      render: (v: number) => branchName(v),
    },
    {
      title: t("activity.registered"),
      render: (_: unknown, r: Activity) =>
        `${r.member_registered_count ?? 0}/${r.max_participants}`,
    },
    {
      title: t("activity.actions"),
      render: (_: unknown, row: Activity) => (
        <Button size="small" onClick={() => openDetail(row)}>
          {t("activity.detail")}
        </Button>
      ),
    },
  ];

  const regColumns = [
    { title: "ID", dataIndex: "id", width: 60 },
    {
      title: t("activity.registrantType"),
      dataIndex: "registrant_type",
      render: (v: string) => t(`registrantType.${v}`),
    },
    { title: t("activity.memberId"), dataIndex: "member_id" },
    { title: t("activity.familyName"), dataIndex: "family_name" },
    {
      title: t("activity.regStatus"),
      dataIndex: "status",
      render: (v: string) => t(`regStatus.${v}`),
    },
    {
      title: t("activity.actions"),
      render: (_: unknown, row: Registration) =>
        row.status === "registered" ? (
          <Button size="small" danger onClick={() => onAbsent(row.id)}>
            {t("activity.markAbsent")}
          </Button>
        ) : null,
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Button type="primary" onClick={() => setOpen(true)}>
        {t("activity.add")}
      </Button>
      <Table rowKey="id" dataSource={rows} columns={columns} pagination={false} />

      <Modal
        title={t("activity.add")}
        open={open}
        onOk={onCreate}
        onCancel={() => setOpen(false)}
        okText={t("activity.submit")}
        cancelText={t("activity.cancel")}
        width={560}
      >
        <Form form={form} layout="vertical" initialValues={{ max_participants: 20 }}>
          <Form.Item name="title" label={t("activity.title")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="activity_type"
            label={t("activity.type")}
            rules={[{ required: true }]}
          >
            <Select
              options={(
                [
                  "weekly_round",
                  "team_building",
                  "course_visit",
                  "networking",
                  "newbie_salon",
                ] as ActivityType[]
              ).map((v) => ({ value: v, label: t(`activityType.${v}`) }))}
            />
          </Form.Item>
          <Form.Item
            name="branch_id"
            label={t("activity.branch")}
            rules={[{ required: true }]}
          >
            <Select
              options={branches.map((b) => ({ value: b.id, label: b.name }))}
            />
          </Form.Item>
          <Form.Item
            name="start_at"
            label={t("activity.startAt")}
            rules={[{ required: true }]}
          >
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="course_name" label={t("activity.course")}>
            <Input />
          </Form.Item>
          <Form.Item name="max_participants" label={t("activity.maxParticipants")}>
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="family_allowed" label={t("activity.familyAllowed")} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="max_family_slots" label={t("activity.maxFamily")}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="course_slots_locked"
            label={t("activity.slotsLocked")}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={detail?.title}
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={720}
      >
        {detail && (
          <Space direction="vertical" style={{ width: "100%" }}>
            {stats && (
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label={t("activity.memberRegistered")}>
                  {stats.member_registered}
                </Descriptions.Item>
                <Descriptions.Item label={t("activity.familyRegistered")}>
                  {stats.family_registered}
                </Descriptions.Item>
                <Descriptions.Item label={t("activity.checkedIn")}>
                  {stats.member_checked_in}
                </Descriptions.Item>
                <Descriptions.Item label={t("activity.attendanceRate")}>
                  {stats.attendance_rate}%
                </Descriptions.Item>
              </Descriptions>
            )}
            <div>
              <div style={{ marginBottom: 8 }}>{t("activity.checkinQr")}</div>
              <QRCode value={`ACT:${detail.id}:${detail.checkin_token}`} />
              <div style={{ color: "#999", fontSize: 12, marginTop: 8 }}>
                {t("activity.checkinHint")}
              </div>
            </div>
            <Table
              rowKey="id"
              size="small"
              dataSource={regs}
              columns={regColumns}
              pagination={false}
            />
          </Space>
        )}
      </Modal>
    </Space>
  );
}
