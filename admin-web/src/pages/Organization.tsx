import { useEffect, useState } from "react";
import {
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  message,
} from "antd";
import { useTranslation } from "react-i18next";

import {
  branchReview,
  captainReview,
  createOrganization,
  createTeam,
  listEnrollments,
  listOrganizations,
  listTeams,
  type Enrollment,
  type EnrollmentStatus,
  type Organization,
  type Team,
} from "../api/org";

export default function OrganizationPage() {
  const { t } = useTranslation();
  return (
    <Tabs
      items={[
        { key: "branch", label: t("org.tabBranch"), children: <BranchTab /> },
        { key: "team", label: t("org.tabTeam"), children: <TeamTab /> },
        {
          key: "enrollment",
          label: t("org.tabEnrollment"),
          children: <EnrollmentTab />,
        },
      ]}
    />
  );
}

function BranchTab() {
  const { t } = useTranslation();
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = () => listOrganizations().then(setOrgs).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  const hq = orgs.find((o) => o.level === "headquarters");

  const onCreate = async () => {
    const values = await form.validateFields();
    if (!hq) return;
    try {
      await createOrganization({ ...values, level: "branch", parent_id: hq.id });
      message.success(t("org.createSuccess"));
      setOpen(false);
      form.resetFields();
      load();
    } catch {
      message.error(t("org.opFailed"));
    }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 70 },
    { title: t("org.name"), dataIndex: "name" },
    {
      title: t("org.level"),
      dataIndex: "level",
      render: (v: string) =>
        v === "headquarters" ? (
          <Tag color="gold">{t("org.headquarters")}</Tag>
        ) : (
          <Tag color="blue">{t("org.branchLevel")}</Tag>
        ),
    },
    { title: t("org.region"), dataIndex: "region" },
    { title: t("org.registrationNo"), dataIndex: "registration_no" },
    {
      title: t("org.status"),
      dataIndex: "is_active",
      render: (v: boolean) =>
        v ? (
          <Tag color="green">{t("org.active")}</Tag>
        ) : (
          <Tag>{t("org.inactive")}</Tag>
        ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Button type="primary" onClick={() => setOpen(true)}>
        {t("org.addBranch")}
      </Button>
      <Table rowKey="id" dataSource={orgs} columns={columns} pagination={false} />
      <Modal
        title={t("org.addBranch")}
        open={open}
        onOk={onCreate}
        onCancel={() => setOpen(false)}
        okText={t("org.submit")}
        cancelText={t("org.cancel")}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t("org.name")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="region" label={t("org.region")}>
            <Input />
          </Form.Item>
          <Form.Item name="registration_no" label={t("org.registrationNo")}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label={t("org.contact")}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

function TeamTab() {
  const { t } = useTranslation();
  const [teams, setTeams] = useState<Team[]>([]);
  const [branches, setBranches] = useState<Organization[]>([]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    listTeams().then(setTeams).catch(() => {});
    listOrganizations()
      .then((os) => setBranches(os.filter((o) => o.level === "branch")))
      .catch(() => {});
  };
  useEffect(() => {
    load();
  }, []);

  const onCreate = async () => {
    const values = await form.validateFields();
    try {
      await createTeam(values);
      message.success(t("org.createSuccess"));
      setOpen(false);
      form.resetFields();
      load();
    } catch {
      message.error(t("org.opFailed"));
    }
  };

  const branchName = (id: number) => branches.find((b) => b.id === id)?.name ?? id;

  const columns = [
    { title: "ID", dataIndex: "id", width: 70 },
    { title: t("org.name"), dataIndex: "name" },
    {
      title: t("org.branch"),
      dataIndex: "branch_id",
      render: (v: number) => branchName(v),
    },
    { title: t("org.homeCourse"), dataIndex: "home_course" },
    {
      title: t("org.status"),
      dataIndex: "is_active",
      render: (v: boolean) =>
        v ? (
          <Tag color="green">{t("org.active")}</Tag>
        ) : (
          <Tag>{t("org.inactive")}</Tag>
        ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Button type="primary" onClick={() => setOpen(true)}>
        {t("org.addTeam")}
      </Button>
      <Table rowKey="id" dataSource={teams} columns={columns} pagination={false} />
      <Modal
        title={t("org.addTeam")}
        open={open}
        onOk={onCreate}
        onCancel={() => setOpen(false)}
        okText={t("org.submit")}
        cancelText={t("org.cancel")}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t("org.name")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="branch_id"
            label={t("org.branch")}
            rules={[{ required: true }]}
          >
            <Select
              options={branches.map((b) => ({ value: b.id, label: b.name }))}
            />
          </Form.Item>
          <Form.Item name="home_course" label={t("org.homeCourse")}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

const STATUS_TAG: Record<EnrollmentStatus, { color: string; key: string }> = {
  pending_captain: { color: "orange", key: "org.statusPendingCaptain" },
  pending_branch: { color: "blue", key: "org.statusPendingBranch" },
  approved: { color: "green", key: "org.statusApproved" },
  rejected: { color: "red", key: "org.statusRejected" },
};

function EnrollmentTab() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Enrollment[]>([]);

  const load = () => listEnrollments().then(setRows).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  const doReview = async (
    fn: (id: number, approve: boolean) => Promise<unknown>,
    id: number,
    approve: boolean
  ) => {
    try {
      await fn(id, approve);
      message.success(t("org.reviewSuccess"));
      load();
    } catch {
      message.error(t("org.opFailed"));
    }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 70 },
    { title: t("org.team"), dataIndex: "team_id" },
    { title: t("org.applicant"), dataIndex: "user_id" },
    {
      title: t("org.status"),
      dataIndex: "status",
      render: (v: EnrollmentStatus) => (
        <Tag color={STATUS_TAG[v].color}>{t(STATUS_TAG[v].key)}</Tag>
      ),
    },
    { title: t("org.remark"), dataIndex: "remark" },
    {
      title: t("org.actions"),
      render: (_: unknown, row: Enrollment) => {
        if (row.status === "pending_captain") {
          return (
            <Space>
              <Button
                size="small"
                type="primary"
                onClick={() => doReview(captainReview, row.id, true)}
              >
                {t("org.captainReview")}: {t("org.approve")}
              </Button>
              <Button
                size="small"
                danger
                onClick={() => doReview(captainReview, row.id, false)}
              >
                {t("org.reject")}
              </Button>
            </Space>
          );
        }
        if (row.status === "pending_branch") {
          return (
            <Space>
              <Button
                size="small"
                type="primary"
                onClick={() => doReview(branchReview, row.id, true)}
              >
                {t("org.branchReview")}: {t("org.approve")}
              </Button>
              <Button
                size="small"
                danger
                onClick={() => doReview(branchReview, row.id, false)}
              >
                {t("org.reject")}
              </Button>
            </Space>
          );
        }
        return null;
      },
    },
  ];

  return <Table rowKey="id" dataSource={rows} columns={columns} pagination={false} />;
}
