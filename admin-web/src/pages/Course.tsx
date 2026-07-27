import { useEffect, useState } from "react";
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from "antd";
import { useTranslation } from "react-i18next";

import { createCourse, listCourses, updateCourse, type Course } from "../api/course";

export default function CoursePage() {
  const { t } = useTranslation();
  const [courses, setCourses] = useState<Course[]>([]);
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const load = () => listCourses().then(setCourses).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  const onOpenCreate = () => {
    setEditingId(null);
    form.resetFields();
    setOpen(true);
  };

  const onOpenEdit = (c: Course) => {
    setEditingId(c.id);
    form.setFieldsValue({
      name_zh: c.name_zh,
      name_en: c.name_en,
      address: c.address,
      city: c.city,
      contact_name: c.contact_name,
      contact_phone: c.contact_phone,
      holes: c.holes,
      par: c.par,
      rating: c.rating ? Number(c.rating) : undefined,
      slope: c.slope,
      remark: c.remark,
      is_active: c.is_active,
    });
    setOpen(true);
  };

  const onSubmit = async () => {
    const v = await form.validateFields();
    try {
      if (editingId) {
        await updateCourse(editingId, v);
      } else {
        await createCourse(v);
      }
      message.success(t("course.saveSuccess"));
      setOpen(false);
      load();
    } catch {
      message.error(t("course.opFailed"));
    }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: t("course.nameZh"), dataIndex: "name_zh" },
    { title: t("course.nameEn"), dataIndex: "name_en" },
    { title: t("course.city"), dataIndex: "city" },
    { title: t("course.holes"), dataIndex: "holes" },
    { title: t("course.par"), dataIndex: "par" },
    { title: t("course.rating"), dataIndex: "rating" },
    { title: t("course.slope"), dataIndex: "slope" },
    {
      title: t("course.status"),
      dataIndex: "is_active",
      render: (v: boolean) => (
        <Tag color={v ? "success" : "default"}>
          {v ? t("org.active") : t("org.inactive")}
        </Tag>
      ),
    },
    {
      title: t("course.actions"),
      render: (_: unknown, row: Course) => (
        <Button size="small" onClick={() => onOpenEdit(row)}>
          {t("course.edit")}
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Button type="primary" onClick={onOpenCreate}>
        {t("course.add")}
      </Button>
      <Table rowKey="id" dataSource={courses} columns={columns} pagination={false} />

      <Modal
        title={editingId ? t("course.edit") : t("course.add")}
        open={open}
        onOk={onSubmit}
        onCancel={() => setOpen(false)}
        okText={t("course.submit")}
        cancelText={t("course.cancel")}
        width={560}
      >
        <Form form={form} layout="vertical" initialValues={{ holes: 18 }}>
          <Form.Item name="name_zh" label={t("course.nameZh")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name_en" label={t("course.nameEn")}>
            <Input />
          </Form.Item>
          <Form.Item name="address" label={t("course.address")}>
            <Input />
          </Form.Item>
          <Form.Item name="city" label={t("course.city")}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label={t("course.contact")}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_phone" label={t("course.phone")}>
            <Input />
          </Form.Item>
          <Form.Item name="holes" label={t("course.holes")}>
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="par" label={t("course.par")}>
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="rating" label={t("course.rating")}>
            <InputNumber min={0} step={0.1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="slope" label={t("course.slope")} extra={t("course.slopeHint")}>
            <InputNumber min={55} max={155} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="remark" label={t("course.remark")}>
            <Input.TextArea rows={2} />
          </Form.Item>
          {editingId && (
            <Form.Item name="is_active" label={t("course.status")} valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </Space>
  );
}
