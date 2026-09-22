/**
 * HoYoDeck 游戏卡片组件
 *
 * 游戏状态 → 按钮逻辑:
 *   启动器未安装 → 提示「请先安装启动器」
 *   游戏未安装   → 「安装」按钮（打开启动器下载）
 *   游戏已安装   → 「启动」+ 「添加到 Steam」按钮
 */
import { useState } from "react";
import { ConfirmModal, showModal, Spinner } from "@decky/ui";
import {
  FaRocket, FaPlus, FaTrash, FaSync,
  FaExclamationCircle, FaStore,
} from "react-icons/fa";
import { addToSteam, removeFromSteam, launchViaScript, refreshArtwork } from "../api";
import { t } from "../i18n";
import type { GameInstallInfo, ShortcutResult } from "../types";

// 游戏封面渐变色（图片加载失败时的兜底）
const GAME_COLORS: Record<string, [string, string]> = {
  hk4e_cn: ["#2476b8", "#73c6d9"],
  hkrpg_cn: ["#28235f", "#7c63c8"],
  nap_cn: ["#242729", "#c9d52a"],
  bh3_cn: ["#3150a8", "#ca75b9"],
  hk4e_global: ["#2476b8", "#73c6d9"],
  hkrpg_global: ["#28235f", "#7c63c8"],
  nap_global: ["#242729", "#c9d52a"],
  bh3_global: ["#3150a8", "#ca75b9"],
};

function getStatusColor(status: string): string {
  switch (status) {
    case "installed": return "#4caf50";
    case "partial": return "#ff9800";
    case "not_installed": return "#9e9e9e";
    default: return "#9e9e9e";
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "installed": return t("installed");
    case "partial": return t("partialInstall");
    case "not_installed": return t("notInstalled");
    default: return status;
  }
}

export function GameCard({
  game,
  onStatusChange,
  launcherReady,
}: {
  game: GameInstallInfo;
  onStatusChange?: () => void;
  launcherReady: boolean;
}) {
  const [launching, setLaunching] = useState(false);
  const [steamAction, setSteamAction] = useState(false);
  const [artworkLoading, setArtworkLoading] = useState(false);
  const [error, setError] = useState<string>();

  const [startColor, endColor] = GAME_COLORS[game.game_id] || ["#26364a", "#58799c"];
  const capsuleUrl = game.artwork_urls?.capsule ?? null;

  // 启动已安装的游戏
  const handleLaunch = async () => {
    setLaunching(true);
    setError(undefined);
    try {
      const result = await launchViaScript(
        game.region as "cn" | "global",
        game.game_id,
        `${game.title} · ${game.region === "cn" ? "国服" : "国际服"}`,
        false,
      );
      if (!result.success) {
        setError(result.error || t("launchFailed"));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLaunching(false);
    }
  };

  // 未安装的游戏：打开启动器下载
  const handleInstallGame = async () => {
    setLaunching(true);
    setError(undefined);
    try {
      const region = game.region as "cn" | "global";
      const label = region === "cn" ? "米哈游启动器" : "HoYoPlay";
      const result = await launchViaScript(region, "launcher", label, false);
      if (result.success) {
        showModal(
          <ConfirmModal
            strTitle="启动器已打开"
            strDescription={`请在 ${label} 中下载 ${game.title}。下载完成后回到 HoYoDeck 刷新游戏列表。`}
            strOKButtonText="好的"
          />
        );
      } else {
        setError(result.error || "启动失败");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLaunching(false);
    }
  };

  const handleAddToSteam = () => {
    showModal(
      <ConfirmModal
        strTitle={t("addToSteam")}
        strDescription={t("confirmAddToSteam")}
        strOKButtonText={t("confirm")}
        strCancelButtonText={t("cancel")}
        onOK={async () => {
          setSteamAction(true);
          setError(undefined);
          try {
            const result: ShortcutResult = await addToSteam(game.game_id);
            if (result.success) {
              onStatusChange?.();
            } else {
              setError(result.error || "Failed");
            }
          } catch (e) {
            setError(String(e));
          } finally {
            setSteamAction(false);
          }
        }}
      />
    );
  };

  const handleRemoveFromSteam = () => {
    showModal(
      <ConfirmModal
        strTitle={t("removeFromSteam")}
        strDescription={t("confirmRemoveFromSteam")}
        strOKButtonText={t("confirm")}
        strCancelButtonText={t("cancel")}
        onOK={async () => {
          setSteamAction(true);
          try {
            await removeFromSteam(game.game_id);
            onStatusChange?.();
          } catch (e) {
            setError(String(e));
          } finally {
            setSteamAction(false);
          }
        }}
      />
    );
  };

  const handleRefreshArtwork = async () => {
    setArtworkLoading(true);
    try {
      await refreshArtwork(game.game_id);
    } catch (e) {
      setError(String(e));
    } finally {
      setArtworkLoading(false);
    }
  };

  return (
    <div style={{
      width: "100%",
      borderRadius: 10,
      overflow: "hidden",
      background: "rgba(255,255,255,.05)",
      border: "1px solid rgba(255,255,255,.08)",
    }}>
      {/* 封面区域 */}
      <div style={{
        width: "100%", height: 140,
        position: "relative", overflow: "hidden",
        background: `linear-gradient(135deg, ${startColor}, ${endColor})`,
      }}>
        {capsuleUrl && (
          <img
            src={capsuleUrl}
            alt=""
            loading="lazy"
            style={{
              position: "absolute", inset: 0,
              width: "100%", height: "100%",
              objectFit: "cover",
            }}
          />
        )}
        {/* 底部渐变遮罩，保证文字可读 */}
        <div style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(to top, rgba(0,0,0,.65) 0%, transparent 60%)",
        }} />
        <div style={{
          position: "absolute", bottom: 12, left: 12, right: 12,
          color: "white", textShadow: "0 2px 8px rgba(0,0,0,.6)",
        }}>
          <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 2 }}>
            {game.region === "cn" ? "国服" : "国际服"}
          </div>
          <div style={{ fontSize: 18, fontWeight: 800, lineHeight: 1.1 }}>
            {game.title}
          </div>
        </div>
        <div style={{
          position: "absolute", top: 8, right: 8,
          padding: "3px 8px", borderRadius: 6,
          fontSize: 10, fontWeight: 600,
          background: getStatusColor(game.status), color: "white",
        }}>
          {getStatusLabel(game.status)}
        </div>
      </div>

      {/* 操作区域 */}
      <div style={{ padding: "10px 12px" }}>
        {game.installed && game.installed_version && (
          <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 8 }}>
            {t("version")}: {game.installed_version}
          </div>
        )}

        {error && (
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "6px 8px", marginBottom: 8, borderRadius: 6,
            background: "rgba(255,107,107,.15)",
            border: "1px solid rgba(255,107,107,.3)",
            fontSize: 12, color: "#ff6b6b",
          }}>
            <FaExclamationCircle size={12} />
            {error}
          </div>
        )}

        {/* 启动器未安装提示 */}
        {!launcherReady && (
          <div style={{
            padding: "8px 10px", marginBottom: 8, borderRadius: 6,
            background: "rgba(255,152,0,.1)",
            border: "1px solid rgba(255,152,0,.2)",
            fontSize: 12, color: "#ff9800",
          }}>
            请先在「环境检查」中安装启动器
          </div>
        )}

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {/* 已安装 → 启动 */}
          {game.installed && (
            <button
              onClick={handleLaunch}
              disabled={launching}
              style={{
                flex: 1, minWidth: 0,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                padding: "8px 12px", borderRadius: 6, border: "none",
                background: "#1a6dcc", color: "white", fontSize: 13, fontWeight: 600,
                cursor: launching ? "wait" : "pointer", opacity: launching ? 0.7 : 1,
              }}
            >
              {launching ? <Spinner width={14} height={14} /> : <FaRocket size={12} />}
              {t("launch")}
            </button>
          )}

          {/* 未安装 + 启动器就绪 → 打开启动器下载游戏 */}
          {!game.installed && launcherReady && (
            <button
              onClick={handleInstallGame}
              disabled={launching}
              style={{
                flex: 1, minWidth: 0,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                padding: "8px 12px", borderRadius: 6, border: "none",
                background: "#e65100", color: "white", fontSize: 13, fontWeight: 600,
                cursor: launching ? "wait" : "pointer", opacity: launching ? 0.7 : 1,
              }}
            >
              {launching ? <Spinner width={14} height={14} /> : <FaStore size={12} />}
              {t("install")}
            </button>
          )}

          {/* Steam 快捷方式（仅已安装游戏） */}
          {game.installed && (
            <button
              onClick={game.has_steam_shortcut ? handleRemoveFromSteam : handleAddToSteam}
              disabled={steamAction}
              style={{
                flex: 1, minWidth: 0,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                padding: "8px 12px", borderRadius: 6,
                border: "1px solid rgba(255,255,255,.15)",
                background: game.has_steam_shortcut ? "rgba(255,107,107,.15)" : "rgba(255,255,255,.08)",
                color: game.has_steam_shortcut ? "#ff6b6b" : "white",
                fontSize: 13, fontWeight: 600,
                cursor: steamAction ? "wait" : "pointer", opacity: steamAction ? 0.7 : 1,
              }}
            >
              {steamAction
                ? <Spinner width={14} height={14} />
                : game.has_steam_shortcut ? <FaTrash size={12} /> : <FaPlus size={12} />
              }
              {game.has_steam_shortcut ? t("removeFromSteam") : t("addToSteam")}
            </button>
          )}
        </div>

        {game.has_steam_shortcut && (
          <button
            onClick={handleRefreshArtwork}
            disabled={artworkLoading}
            style={{
              width: "100%", marginTop: 6,
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              padding: "6px 12px", borderRadius: 6, border: "none",
              background: "transparent",
              color: "rgba(255,255,255,.6)", fontSize: 12,
              cursor: artworkLoading ? "wait" : "pointer",
            }}
          >
            {artworkLoading ? <Spinner width={12} height={12} /> : <FaSync size={10} />}
            {t("refreshArtwork")}
          </button>
        )}
      </div>
    </div>
  );
}
