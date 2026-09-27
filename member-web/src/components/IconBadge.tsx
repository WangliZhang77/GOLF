import type { CSSProperties, ReactNode } from "react";

export default function IconBadge({
  icon,
  color = "#1f7a3d",
  background = "#e8f5e9",
  size = 36,
  style,
}: {
  icon: ReactNode;
  color?: string;
  background?: string;
  size?: number;
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background,
        color,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.5,
        flexShrink: 0,
        ...style,
      }}
    >
      {icon}
    </div>
  );
}
