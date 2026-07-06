import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  message,
} from "antd";
import { useTranslation } from "react-i18next";

import {
  createLedger,
  getSummary,
  listLedger,
  markPaid,
  reconcileLedger,
  refundLedger,
  voidLedger,
  type Ledger,
  type LedgerDirection,
  type LedgerSummary,
} from "../api/finance";
import { listMembers, type Member } from "../api/member";
import { listOrganizations, type Organization } from "../api/org";

const STATUS_COLOR: Record<string, string> = {
  confirmed: "success",
  voided: "default",
  refunded: "warning",
};

export default function FinancePage() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Ledger[]>([]);
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [branches, setBranches] = useState<Organization[]>([]);
  const [open, setOpen] = useState(false);
  const [voidOpen, setVoidOpen] = useState(false);
  const [voidId, setVoidId] = useState<number | null>(null);
  const [filterDir, setFilterDir] = useState<LedgerDirection | undefined>();
  const [form] = Form.useForm();
  const [voidForm] = Form.useForm();

  const load = async () => {
    try {
      const [list, sum] = await Promise.all([
        listLedger(filterDir ? { direction: filterDir } : undefined),
        getSummary(),
      ]);
      setRows(list);
      setSummary(sum);
    } catch {
      message.error(t("finance.opFailed"));
    }
  };

  useEffect(() => {
    load();
    listMembers()
      .then(setMembers)
      .catch(() => {});
    listOrganizations()
      .then((os) => setBranches(os.filter((o) => o.level === "branch")))
      .catch(() => {});
  }, [filterDir]);

  const onCreate = async () => {
    const v = await form.validateFields();
    try {
      await createLedger({
        direction: v.direction,
        category: v.category,
        amount: v.amount,
        title: v.title,
        remark: v.remark,
        member_id: v.member_id,
        branch_id: v.branch_id,
        is_paid: v.is_paid,
      });
      message.success(t("finance.createSuccess"));
      setOpen(false);
      form.resetFields();
      load();
    } catch {
      message.error(t("finance.opFailed"));
    }
  };

  const onVoid = async () => {
    if (voidId === null) return;
    const v = await voidForm.validateFields();
    try {
      await voidLedger(voidId, v.reason);
      message.success(t("finance.voidSuccess"));
      setVoidOpen(false);
      voidForm.resetFields();
      load();
    } catch {
      message.error(t("finance.opFailed"));
    }
  };

  const incomeCategories = [
    "annual_dues",
    "event_registration",
    "sponsorship",
    "course_subsidy",
    "donation",
    "other",
  ];
  const expenseCategories = [
    "course_fee",
    "event_supplies",
    "referee_subsidy",
    "trophy_prize",
    "admin_expense",
    "payment_fee",
    "other",
  ];

  const direction = Form.useWatch("direction", form) as LedgerDirection | undefined;
  const categories =
    direction === "expense" ? expenseCategories : incomeCategories;

  const memberName = (id: number | null) =>
    id ? members.find((m) => m.id === id)?.chinese_name ?? id : "-";

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    {
      title: t("finance.direction"),
      dataIndex: "direction",
      render: (d: string) => (
        <Tag color={d === "income" ? "green" : "red"}>
          {t(`finance.dir.${d}`)}
        </Tag>
      ),
    },
    {
      title: t("finance.category"),
      dataIndex: "category",
      render: (c: string) => t(`finance.cat.${c}`, c),
    },
    { title: t("finance.title"), dataIndex: "title" },
    {
      title: t("finance.amount"),
      dataIndex: "amount",
      render: (a: string, r: Ledger) => `${r.currency} ${a}`,
    },
    {
      title: t("finance.member"),
      dataIndex: "member_id",
      render: (id: number | null) => memberName(id),
    },
    {
      title: t("finance.statusLabel"),
      dataIndex: "status",
      render: (s: string) => (
        <Tag color={STATUS_COLOR[s]}>{t(`finance.status.${s}`)}</Tag>
      ),
    },
    {
      title: t("finance.paid"),
      dataIndex: "is_paid",
      render: (p: boolean, r: Ledger) =>
        r.direction === "income" && ["annual_dues", "event_registration"].includes(r.category) ? (
          <Tag color={p ? "success" : "warning"}>
            {p ? t("finance.paidYes") : t("finance.paidNo")}
          </Tag>
        ) : (
          "-"
        ),
    },
    {
      title: t("finance.reconciled"),
      dataIndex: "reconciled",
      render: (r: boolean) =>
        r ? <Tag color="blue">{t("finance.reconciledYes")}</Tag> : "-",
    },
    {
      title: t("finance.actions"),
      key: "actions",
      render: (_: unknown, r: Ledger) =>
        r.status === "confirmed" ? (
          <Space size="small" wrap>
            {!r.reconciled && (
              <Button
                size="small"
                onClick={() =>
                  reconcileLedger(r.id).then(load).catch(() =>
                    message.error(t("finance.opFailed"))
                  )
                }
              >
                {t("finance.reconcile")}
              </Button>
            )}
            {r.direction === "income" &&
              !r.is_paid &&
              ["annual_dues", "event_registration"].includes(r.category) && (
                <Button
                  size="small"
                  type="primary"
                  onClick={() =>
                    markPaid(r.id).then(load).catch(() =>
                      message.error(t("finance.opFailed"))
                    )
                  }
                >
                  {t("finance.markPaid")}
                </Button>
              )}
            {r.direction === "income" && r.is_paid && (
              <Button
                size="small"
                onClick={() =>
                  refundLedger(r.id).then(load).catch(() =>
                    message.error(t("finance.opFailed"))
                  )
                }
              >
                {t("finance.refund")}
              </Button>
            )}
            <Button
              size="small"
              danger
              onClick={() => {
                setVoidId(r.id);
                setVoidOpen(true);
              }}
            >
              {t("finance.void")}
            </Button>
          </Space>
        ) : null,
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      {summary && (
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t("finance.totalIncome")}
                value={summary.total_income}
                prefix="NZD"
                valueStyle={{ color: "#3f8600" }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t("finance.totalExpense")}
                value={summary.total_expense}
                prefix="NZD"
                valueStyle={{ color: "#cf1322" }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title={t("finance.net")} value={summary.net} prefix="NZD" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t("finance.unreconciled")}
                value={summary.unreconciled_count}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Space>
        <Select
          allowClear
          placeholder={t("finance.filterDirection")}
          style={{ width: 140 }}
          value={filterDir}
          onChange={setFilterDir}
          options={[
            { value: "income", label: t("finance.dir.income") },
            { value: "expense", label: t("finance.dir.expense") },
          ]}
        />
        <Button type="primary" onClick={() => setOpen(true)}>
          {t("finance.add")}
        </Button>
        <Button onClick={load}>{t("common.refresh")}</Button>
      </Space>

      <Table rowKey="id" dataSource={rows} columns={columns} pagination={{ pageSize: 15 }} />

      <Modal
        title={t("finance.add")}
        open={open}
        onOk={onCreate}
        onCancel={() => setOpen(false)}
        okText={t("finance.submit")}
        cancelText={t("finance.cancel")}
      >
        <Form form={form} layout="vertical" initialValues={{ direction: "income" }}>
          <Form.Item name="direction" label={t("finance.direction")} rules={[{ required: true }]}>
            <Select
              options={[
                { value: "income", label: t("finance.dir.income") },
                { value: "expense", label: t("finance.dir.expense") },
              ]}
            />
          </Form.Item>
          <Form.Item name="category" label={t("finance.category")} rules={[{ required: true }]}>
            <Select options={categories.map((c) => ({ value: c, label: t(`finance.cat.${c}`) }))} />
          </Form.Item>
          <Form.Item name="title" label={t("finance.title")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="amount" label={t("finance.amount")} rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.01} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="member_id" label={t("finance.member")}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={members.map((m) => ({
                value: m.id,
                label: `${m.chinese_name} (#${m.id})`,
              }))}
            />
          </Form.Item>
          <Form.Item name="branch_id" label={t("finance.branch")}>
            <Select
              allowClear
              options={branches.map((b) => ({ value: b.id, label: b.name }))}
            />
          </Form.Item>
          {direction === "income" && (
            <Form.Item name="is_paid" label={t("finance.paid")} initialValue={false}>
              <Select
                options={[
                  { value: false, label: t("finance.paidNo") },
                  { value: true, label: t("finance.paidYes") },
                ]}
              />
            </Form.Item>
          )}
          <Form.Item name="remark" label={t("finance.remark")}>
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={t("finance.void")}
        open={voidOpen}
        onOk={onVoid}
        onCancel={() => setVoidOpen(false)}
        okText={t("finance.submit")}
        cancelText={t("finance.cancel")}
      >
        <Form form={voidForm} layout="vertical">
          <Form.Item
            name="reason"
            label={t("finance.voidReason")}
            rules={[{ required: true }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
