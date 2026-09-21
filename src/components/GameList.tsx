/**
 * HoYoDeck 游戏列表组件
 *
 * 国服/国际服分段切换 + 网格布局。
 * 使用 Decky Focusable 处理 Steam Deck 手柄导航。
 * 同时获取环境状态，将 launcherReady 传给每个 GameCard。
 */
import { useEffect, useState } from "react";
import { Focusable, Spinner } from "@decky/ui";
import { getGames, checkEnvironment } from "../api";
import { t } from "../i18n";
import { GameCard } from "./GameCard";
import type { GameInstallInfo } from "../types";
import type { EnvCheckResult } from "../api";

type FilterTab = "cn" | "global";

export function GameList() {
  const [games, setGames] = useState<GameInstallInfo[] | null>(null);
  const [env, setEnv] = useState<EnvCheckResult | null>(null);
  const [filter, setFilter] = useState<FilterTab>("cn");
  const [error, setError] = useState<string>();

  const refreshGames = () => {
    getGames()
      .then(setGames)
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    refreshGames();
    checkEnvironment().then(setEnv).catch(() => {});
  }, []);

  const filteredGames = games?.filter((game) => {
    return game.region === filter;
  }) ?? [];

  if (!games && !error) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
        <Spinner width={48} height={48} />
      </div>
    );
  }

  const tabs = ["cn", "global"] as const;
  const tabLabels = { cn: t("cnGames"), global: t("globalGames") };
  const tabIndex = tabs.indexOf(filter);

  return (
    <div style={{ padding: "8px 8px 80px" }}>
      {/* 分段切换控件 */}
      <div style={{
        display: "flex", justifyContent: "center", marginBottom: 16, padding: "0 4px",
      }}>
        <div style={{
          position: "relative", display: "inline-flex",
          padding: 3, borderRadius: 8,
          background: "rgba(255,255,255,.06)",
          border: "1px solid rgba(255,255,255,.1)",
        }}>
          {/* 滑块 */}
          <div style={{
            position: "absolute", top: 3, bottom: 3,
            width: `calc(${100 / tabs.length}% - 2px)`,
            left: `calc(${tabIndex * (100 / tabs.length)}% + 1px)`,
            borderRadius: 6,
            background: "#1a6dcc",
            boxShadow: "0 1px 4px rgba(0,0,0,.3)",
            transition: "left 200ms cubic-bezier(.4,0,.2,1)",
          }} />
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              style={{
                position: "relative", zIndex: 1,
                padding: "7px 20px",
                border: "none", borderRadius: 6,
                background: "transparent",
                color: filter === tab ? "#fff" : "rgba(255,255,255,.55)",
                fontSize: 13, fontWeight: filter === tab ? 600 : 400,
                cursor: "pointer",
                transition: "color 200ms",
                whiteSpace: "nowrap",
              }}
            >
              {tabLabels[tab]}
            </button>
          ))}
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={{ color: "#ff6b6b", padding: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* 游戏网格 */}
      {filteredGames.length === 0 ? (
        <div style={{
          textAlign: "center",
          padding: 40,
          opacity: 0.5,
          fontSize: 14,
        }}>
          {t("noGamesInstalled")}
        </div>
      ) : (
        <Focusable
          flow-children="grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: 12,
          }}
        >
          {filteredGames.map((game) => (
            <Focusable key={game.game_id}>
              <GameCard
                game={game}
                onStatusChange={refreshGames}
                launcherReady={
                  game.region === "cn"
                    ? env?.launcher_cn?.ready ?? false
                    : env?.launcher_global?.ready ?? false
                }
              />
            </Focusable>
          ))}
        </Focusable>
      )}
    </div>
  );
}
