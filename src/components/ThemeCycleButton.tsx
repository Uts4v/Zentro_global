import { useTheme } from "@/lib/theme";
import { Sun, Moon, Monitor } from "lucide-react";

export function ThemeCycleButton({ className = "" }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  const nextTheme = () => {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  };

  const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;

  return (
    <button
      onClick={nextTheme}
      className={`grid h-8 w-8 place-items-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors ${className}`}
      title={`Theme: ${theme}`}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
