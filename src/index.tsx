/**
 * HoYoDeck — 米哈游游戏管理器
 * Decky Loader 插件主入口
 */
import { definePlugin } from "@decky/api";
import { staticClasses } from "@decky/ui";
import { FaGamepad } from "react-icons/fa";

import { DashboardPanel } from "./components/Dashboard";
import { GameList } from "./components/GameList";
import { t } from "./i18n";

export default definePlugin(() => {
  console.log("[HoYoDeck] 插件前端已加载");
  return {
    name: "HoYoDeck",
    titleView: <div className={staticClasses.Title}>{t("appName")}</div>,
    icon: <FaGamepad />,
    content: (
      <div style={{ minHeight: "100%" }}>
        <DashboardPanel />
        <GameList />
      </div>
    ),
    onDismount() {
      // 清理工作
    },
  };
});
