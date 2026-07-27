import { useEffect, useState } from "react";
import {
  Button,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from "antd";
import { useTranslation } from "react-i18next";

import { listCompetitions, type Competition } from "../api/competition";
import {
  createContract,
  createSponsor,
  listContracts,
  listSponsors,
  updateSponsor,
  type Sponsor,
  type SponsorContract,
} from "../api/sponsor";

export default function SponsorPage() {
  const { t } = useTranslation();
  const [sponsors, setSponsors] = useState<Sponsor[]>([]);
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Sponsor | null>(null);
  const [contracts, setContracts] = useState<SponsorContract[]>([]);
  const [form] = Form.useForm();
  const [contractForm] = Form.useForm();

  const load = () => listSponsors().then(setSponsors).catch(() => {});
  useEffect(() => {
    load();
    listCompetitions().then(setCompetitions).catch(() => {});
  }, []);

  const onOpenCreate = () => {
    setEditingId(null);
    form.resetFields();
    setOpen(true);
  };

  const onOpenEdit = (s: Sponsor) => {
    setEditingId(s.id);
    form.setFieldsValue(s);
    setOpen(true);
  };

  const onSubmit = async () => {
    const v = await form.validateFields();
    try {
      if (editingId) {
        await updateSponsor(editingId, v);
      } else {
        await createSponsor(v);
      }
      message.success(t("sponsor.saveSuccess"));
      setOpen(false);
      load();
    } catch {
      message.error(t("sponsor.opFailed"));
    }
  };

  const openDetail = async (s: Sponsor) => {
    setDetail(s);
    contractForm.resetFields();
    try {
      setContracts(await listContracts(s.id));
    } catch {
      message.error(t("sponsor.opFailed"));
    }
  };

  const onAddContract = async () => {
    if (!detail) return;
    const v = await contractForm.validateFields();
    try {
      await createContract(detail.id, {
        competition_id: v.competition_id,
        amount: v.amount,
        start_date: v.start_date.format("YYYY-MM-DD"),
        end_date: v.end_date ? v.end_date.format("YYYY-MM-DD") : undefined,
        benefit: v.benefit,
      });
      message.success(t("sponsor.contractSaveSuccess"));
      contractForm.resetFields();
      setContracts(await listContracts(detail.id));
    } catch {
      message.error(t("sponsor.opFailed"));
    }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: t("sponsor.companyName"), dataIndex: "company_name" },
    { title: t("sponsor.industry"), dataIndex: "industry" },
    { title: t("sponsor.level"), dataIndex: "level" },
    { title: t("sponsor.contact"), dataIndex: "contact_name" },
    {
      title: t("sponsor.status"),
      dataIndex: "is_active",
      render: (v: boolean) => (
        <Tag color={v ? "success" : "default"}>{v ? t("org.active") : t("org.inactive")}</Tag>
      ),
    },
    {
      title: t("sponsor.actions"),
      render: (_: unknown, row: Sponsor) => (
        <Space>
          <Button size="small" onClick={() => onOpenEdit(row)}>
            {t("sponsor.edit")}
          </Button>
          <Button size="small" onClick={() => openDetail(row)}>
            {t("sponsor.contracts")}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Button type="primary" onClick={onOpenCreate}>
        {t("sponsor.add")}
      </Button>
      <Table rowKey="id" dataSource={sponsors} columns={columns} pagination={false} />

      <Modal
        title={editingId ? t("sponsor.edit") : t("sponsor.add")}
        open={open}
        onOk={onSubmit}
        onCancel={() => setOpen(false)}
        okText={t("sponsor.submit")}
        cancelText={t("sponsor.cancel")}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="company_name"
            label={t("sponsor.companyName")}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="industry" label={t("sponsor.industry")}>
            <Input />
          </Form.Item>
          <Form.Item name="level" label={t("sponsor.level")}>
            <Input placeholder="金牌/银牌" />
          </Form.Item>
          <Form.Item name="contact_name" label={t("sponsor.contact")}>
            <Input />
          </Form.Item>
          <Form.Item name="phone" label={t("sponsor.phone")}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label={t("sponsor.email")}>
            <Input />
          </Form.Item>
          <Form.Item name="website" label={t("sponsor.website")}>
            <Input />
          </Form.Item>
          {editingId && (
            <Form.Item name="is_active" label={t("sponsor.status")} valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal
        title={`${t("sponsor.contracts")} - ${detail?.company_name ?? ""}`}
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={680}
      >
        {detail && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Form form={contractForm} layout="inline">
              <Form.Item name="competition_id" label={t("sponsor.linkedCompetition")}>
                <Select
                  allowClear
                  style={{ width: 160 }}
                  options={competitions.map((c) => ({ value: c.id, label: c.name }))}
                />
              </Form.Item>
              <Form.Item name="amount" rules={[{ required: true }]}>
                <InputNumber min={0} placeholder={t("sponsor.amount")} />
              </Form.Item>
              <Form.Item name="start_date" rules={[{ required: true }]}>
                <DatePicker placeholder={t("sponsor.startDate")} />
              </Form.Item>
              <Form.Item name="end_date">
                <DatePicker placeholder={t("sponsor.endDate")} />
              </Form.Item>
              <Form.Item name="benefit">
                <Input placeholder={t("sponsor.benefit")} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" onClick={onAddContract}>
                  {t("sponsor.addContract")}
                </Button>
              </Form.Item>
            </Form>
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={contracts}
              columns={[
                { title: t("sponsor.amount"), dataIndex: "amount" },
                { title: t("sponsor.startDate"), dataIndex: "start_date" },
                { title: t("sponsor.endDate"), dataIndex: "end_date" },
                { title: t("sponsor.linkedCompetition"), dataIndex: "competition_id" },
                { title: t("sponsor.benefit"), dataIndex: "benefit" },
              ]}
            />
          </Space>
        )}
      </Modal>
    </Space>
  );
}
