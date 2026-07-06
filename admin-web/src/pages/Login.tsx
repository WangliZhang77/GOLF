import { useState } from "react";
import { Button, Card, Form, Input, Select, Space, Typography, message } from "antd";
import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { SUPPORTED_LANGS, type Lang } from "../i18n";

const { Title } = Typography;

export default function Login() {
  const { t, i18n } = useTranslation();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success(t("login.success"));
    } catch {
      message.error(t("login.failed"));
    } finally {
      setLoading(false);
    }
  };

  const changeLang = (lang: Lang) => {
    i18n.changeLanguage(lang);
    localStorage.setItem("lang", lang);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f0f2f5",
      }}
    >
      <Card style={{ width: 380 }}>
        <Space
          direction="vertical"
          size="large"
          style={{ width: "100%", textAlign: "center" }}
        >
          <Title level={4} style={{ color: "#1f7a3d", marginBottom: 0 }}>
            {t("login.title")}
          </Title>
          <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
            <Form.Item
              name="username"
              rules={[{ required: true, message: t("login.usernameRequired") }]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder={t("login.username")}
                size="large"
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[{ required: true, message: t("login.passwordRequired") }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder={t("login.password")}
                size="large"
              />
            </Form.Item>
            <Form.Item style={{ marginBottom: 8 }}>
              <Button type="primary" htmlType="submit" block size="large" loading={loading}>
                {t("login.submit")}
              </Button>
            </Form.Item>
          </Form>
          <Select<Lang>
            value={i18n.language as Lang}
            style={{ width: 120 }}
            onChange={changeLang}
            options={SUPPORTED_LANGS.map((l) => ({
              value: l,
              label: l === "zh-CN" ? "简体中文" : "English",
            }))}
          />
        </Space>
      </Card>
    </div>
  );
}
