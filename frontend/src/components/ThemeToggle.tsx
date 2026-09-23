import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function initial(): Theme {
  try {
    const saved = localStorage.getItem("kw-theme") as Theme | null;
    if (saved) return saved;
  } catch {
    // private 모드 등에서 접근이 막힌다. OS 설정으로 넘어간다.
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(initial);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("kw-theme", theme);
    } catch {
      // 저장 못 해도 이번 세션은 정상 동작한다.
    }
  }, [theme]);

  return (
    <button
      className="grid h-9 w-9 place-items-center rounded-full text-base"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      title="테마 전환"
      aria-label="테마 전환"
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
