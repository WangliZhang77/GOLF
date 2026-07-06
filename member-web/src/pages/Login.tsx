import { useState } from "react";
import { Button, Form, Input, NavBar, Toast } from "antd-mobile";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { type Lang } from "../i18n";

export default function Login() {
  const { t, i18n } = useTranslation();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
    } catch {
      Toast.show({ content: t("login.failed") });
    } finally {
      setLoading(false);
    }
  };

  const toggleLang = () => {
    const next: Lang = i18n.language === "en" ? "zh-CN" : "en";
    i18n.changeLanguage(next);
    localStorage.setItem("lang", next);
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <NavBar
        backArrow={false}
        right={
          <Button size="mini" fill="none" onClick={toggleLang}>
            {i18n.language === "en" ? "中文" : "EN"}
          </Button>
        }
      >
        {t("login.title")}
      </NavBar>
      <div style={{ padding: 16, marginTop: 24 }}>
        <Form
          layout="vertical"
          onFinish={onFinish}
          footer={
            <Button block type="submit" color="primary" loading={loading}>
              {t("login.submit")}
            </Button>
          }
        >
          <Form.Item name="username" label={t("login.username")} rules={[{ required: true }]}>
            <Input placeholder={t("login.username")} />
          </Form.Item>
          <Form.Item name="password" label={t("login.password")} rules={[{ required: true }]}>
            <Input type="password" placeholder={t("login.password")} />
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}
