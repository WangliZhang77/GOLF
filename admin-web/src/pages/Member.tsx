import { useEffect, useState } from "react";
import {
  Button,
  Descriptions,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  message,
} from "antd";
import { useTranslation } from "react-i18next";

import {
  adjustHandicap,
  getMemberHandicap,
  type HandicapDashboard,
} from "../api/handicap";
import {
  blacklistMember,
  createMember,
  listMembers,
  promoteMember,
  sleepScan,
  type Member,
  type MemberLevel,
  type MemberStatus,
} from "../api/member";
import { listOrganizations, type Organization } from "../api/org";

const LEVEL_COLOR: Record<MemberLevel, string> = {
  honorary: "gold",
  formal: "green",
  probationary: "blue",
  blacklist: "red",
};
const STATUS_COLOR: Record<MemberStatus, string> = {
  active: "green",
  sleeping: "orange",
  cancelled: "default",
};

export default function MemberPage() {
  const { t } = useTranslation();
  const [members, setMembers] = useState<Member[]>([]);
  const [branches, setBranches] = useState<Organization[]>([]);
  const [open, setOpen] = useState(false);
  const [handicapTarget, setHandicapTarget] = useState<Member | null>(null);
  const [handicapDashboard, setHandicapDashboard] = useState<HandicapDashboard | null>(null);
  const [form] = Form.useForm();
  const [handicapForm] = Form.useForm();

  const load = () => {
    listMembers().then(setMembers).catch(() => {});
    listOrganizations()
      .then((os) => setBranches(os.filter((o) => o.level === "branch")))
      .catch(() => {});
  };
  useEffect(() => {
    load();
  }, []);

  const branchName = (id: number | null) =>
    id ? branches.find((b) => b.id === id)?.name ?? id : "-";

  const onCreate = async () => {
    const values = await form.validateFields();
    try {
      await createMember(values);
      message.success(t("member.createSuccess"));
      setOpen(false);
      form.resetFields();
      load();
    } catch {
      message.error(t("member.opFailed"));
    }
  };

  const onBlacklist = async (id: number) => {
    try {
      await blacklistMember(id);
      load();
    } catch {
      message.error(t("member.opFailed"));
    }
  };

  const onPromote = async (id: number) => {
    try {
      const res = await promoteMember(id);
      if (res.promoted) message.success(t("member.promoteOk"));
      else message.warning(t("member.promoteNo"));
      load();
    } catch {
      message.error(t("member.opFailed"));
    }
  };

  const onSleepScan = async () => {
    try {
      const res = await sleepScan();
      message.success(t("member.sleepDone") + res.marked_sleeping);
      load();
    } catch {
      message.error(t("member.opFailed"));
    }
  };

  const onOpenHandicap = async (row: Member) => {
    setHandicapTarget(row);
    handicapForm.resetFields();
    try {
      setHandicapDashboard(await getMemberHandicap(row.id));
    } catch {
      message.error(t("member.opFailed"));
    }
  };

  const onAdjustHandicap = async () => {
    if (!handicapTarget) return;
    const v = await handicapForm.validateFields();
    try {
      const updated = await adjustHandicap(handicapTarget.id, v.new_handicap, v.remark);
      setHandicapDashboard(updated);
      handicapForm.resetFields();
      message.success(t("handicap.adjustSuccess"));
      load();
    } catch {
      message.error(t("member.opFailed"));
    }
  };

  const hasPrivate = members.some((m) => m.passport_no !== undefined);

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: t("member.chineseName"), dataIndex: "chinese_name" },
    { title: t("member.englishName"), dataIndex: "english_name" },
    {
      title: t("member.branch"),
      dataIndex: "branch_id",
      render: (v: number | null) => branchName(v),
    },
    {
      title: t("member.level"),
      dataIndex: "level",
      render: (v: MemberLevel) => (
        <Tag color={LEVEL_COLOR[v]}>{t(`level.${v}`)}</Tag>
      ),
    },
    {
      title: t("member.status"),
      dataIndex: "status",
      render: (v: MemberStatus) => (
        <Tag color={STATUS_COLOR[v]}>{t(`memberStatus.${v}`)}</Tag>
      ),
    },
    ...(hasPrivate
      ? [
          {
            title: t("member.phone"),
            dataIndex: "local_phone",
            render: (v: string | null) => v || "-",
          },
          {
            title: t("member.passport"),
            dataIndex: "passport_no",
            render: (v: string | null) => v || "-",
          },
        ]
      : []),
    {
      title: t("member.actions"),
      render: (_: unknown, row: Member) => (
        <Space>
          <Button size="small" onClick={() => onOpenHandicap(row)}>
            {t("handicap.adjust")}
          </Button>
          {row.level === "probationary" && (
            <Button size="small" type="primary" onClick={() => onPromote(row.id)}>
              {t("member.promote")}
            </Button>
          )}
          {row.level !== "blacklist" && (
            <Popconfirm
              title={t("member.blacklist")}
              onConfirm={() => onBlacklist(row.id)}
            >
              <Button size="small" danger>
                {t("member.blacklist")}
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Space>
        <Button type="primary" onClick={() => setOpen(true)}>
          {t("member.add")}
        </Button>
        <Button onClick={onSleepScan}>{t("member.sleepScan")}</Button>
      </Space>
      {!hasPrivate && (
        <div style={{ color: "#999", fontSize: 12 }}>{t("member.privateHint")}</div>
      )}
      <Table rowKey="id" dataSource={members} columns={columns} pagination={false} />

      <Modal
        title={t("member.add")}
        open={open}
        onOk={onCreate}
        onCancel={() => setOpen(false)}
        okText={t("member.submit")}
        cancelText={t("member.cancel")}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="chinese_name"
            label={t("member.chineseName")}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="english_name" label={t("member.englishName")}>
            <Input />
          </Form.Item>
          <Form.Item name="branch_id" label={t("member.branch")}>
            <Select
              allowClear
              options={branches.map((b) => ({ value: b.id, label: b.name }))}
            />
          </Form.Item>
          <Form.Item name="local_phone" label={t("member.phone")}>
            <Input />
          </Form.Item>
          <Form.Item name="passport_no" label={t("member.passport")}>
            <Input />
          </Form.Item>
          <Form.Item name="account_username" label={t("member.account")}>
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item name="account_password" label={t("member.password")}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`${t("handicap.adjust")} - ${handicapTarget?.chinese_name ?? ""}`}
        open={!!handicapTarget}
        onCancel={() => setHandicapTarget(null)}
        footer={null}
        width={480}
      >
        {handicapDashboard && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label={t("handicap.current")}>
                {handicapDashboard.current_handicap ?? "-"}
              </Descriptions.Item>
              <Descriptions.Item label={t("handicap.trend")}>
                {t(`handicapTrend.${handicapDashboard.trend}`)}
              </Descriptions.Item>
            </Descriptions>
            <Form form={handicapForm} layout="inline">
              <Form.Item name="new_handicap" rules={[{ required: true }]}>
                <InputNumber
                  min={0}
                  max={54}
                  step={0.1}
                  placeholder={t("handicap.newValue")}
                />
              </Form.Item>
              <Form.Item name="remark">
                <Input placeholder={t("handicap.remark")} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" onClick={onAdjustHandicap}>
                  {t("handicap.submit")}
                </Button>
              </Form.Item>
            </Form>
            <List
              size="small"
              header={t("handicap.history")}
              bordered
              dataSource={handicapDashboard.history}
              renderItem={(h) => (
                <List.Item>
                  {h.date} · {h.old_handicap ?? "-"} → {h.new_handicap}
                  {h.remark ? ` · ${h.remark}` : ""}
                </List.Item>
              )}
              locale={{ emptyText: t("handicap.noHistory") }}
            />
          </Space>
        )}
      </Modal>
    </Space>
  );
}
