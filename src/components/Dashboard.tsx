/**
 * HoYoDeck 仪表盘组件
 *
 * 组件层级:
 *   DashboardPanel          — 主面板，管理环境检查折叠状态
 *     ├─ EnvItem            — 单个环境检查项（UMU、Proton、Steam 目录）
 *     ├─ LauncherItem       — 启动器管理（Switch 切换国服/国际服 + 下载进度条）
 *     └─ 清理按钮           — 移除插件环境 / 移除环境+游戏
 */
import { useEffect, useState } from "react";
import { PanelSection, PanelSectionRow, Spinner } from "@decky/ui";
import { ConfirmModal, showModal } from "@decky/ui";
import {
  FaCheckCircle, FaExclamationTriangle, FaSync, FaCog,
  FaChevronDown, FaChevronRight, FaRocket, FaDownload, FaStore, FaTrash,
} from "react-icons/fa";
import { getDashboard, checkEnvironment, installComponent, launchViaScript, getDownloadProgress, cleanupEnvironment, cleanupAll, type EnvCheckResult, type EnvCheckItem } from "../api";
import { t } from "../i18n";
import type { Dashboard } from "../types";

// ─── Switch 切换控件 ──────────────────────────────────────

function SegmentedSwitch({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  const idx = options.findIndex(o => o.value === value);
  return (
    <div style={{
      display: "inline-flex", position: "relative",
      background: "rgba(255,255,255,.08)", borderRadius: 16,
      padding: 2, gap: 0,
    }}>
      {options.map((opt, i) => (
        <div
          key={opt.value}
          onClick={() => onChange(opt.value)}
          style={{
            padding: "4px 12px", borderRadius: 14, fontSize: 11, fontWeight: 600,
            cursor: "pointer", userSelect: "none", zIndex: 1, position: "relative",
            color: i === idx ? "white" : "rgba(255,255,255,.5)",
            transition: "color 0.2s",
          }}
        >
          {opt.label}
        </div>
      ))}
      {/* 滑块 */}
      <div style={{
        position: "absolute", top: 2, left: 2,
        width: `${100 / options.length}%`,
        height: "calc(100% - 4px)",
        borderRadius: 14, background: "#1a6dcc",
        transform: `translateX(${idx * 100}%)`,
        transition: "transform 0.2s cubic-bezier(.4,0,.2,1)",
      }} />
    </div>
  );
}

// ─── 单个环境检查项 ────────────────────────────────────────

function EnvItem({
  item,
  componentKey,
  onDone,
}: {
  item: EnvCheckItem;
  componentKey: string;
  onDone: () => void;
}) {
  const [installing, setInstalling] = useState(false);
  const [msg, setMsg] = useState<string>();

  const handleClick = async () => {
    setInstalling(true);
    setMsg(undefined);
    try {
      const res = await installComponent(componentKey);
      setMsg(res.detail);
      onDone();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setInstalling(false);
    }
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "8px 10px", borderRadius: 6,
      background: item.ready ? "rgba(76,175,80,.08)" : "rgba(255,152,0,.08)",
      border: `1px solid ${item.ready ? "rgba(76,175,80,.2)" : "rgba(255,152,0,.2)"}`,
    }}>
      {item.ready
        ? <FaCheckCircle color="#4caf50" size={14} />
        : <FaExclamationTriangle color="#ff9800" size={14} />
      }
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{item.name}</div>
        <div style={{
          fontSize: 11, opacity: 0.7,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{item.detail}</div>
        {msg && (
          <div style={{
            fontSize: 11, marginTop: 2,
            color: msg.includes("成功") || msg.includes("已存在") ? "#4caf50" : "#ff6b6b",
          }}>{msg}</div>
        )}
      </div>
      <button
        onClick={handleClick}
        disabled={installing}
        style={{
          display: "flex", alignItems: "center", gap: 4,
          padding: "4px 10px", borderRadius: 5,
          border: "1px solid rgba(255,255,255,.15)",
          background: item.ready ? "rgba(76,175,80,.15)" : "rgba(255,255,255,.06)",
          color: item.ready ? "#4caf50" : "rgba(255,255,255,.8)",
          fontSize: 11, fontWeight: item.ready ? 600 : 400,
          cursor: installing ? "wait" : "pointer",
          opacity: installing ? 0.6 : 1, whiteSpace: "nowrap",
        }}
      >
        {installing ? <Spinner width={10} height={10} /> : <FaSync size={10} />}
        {item.ready ? "重装" : "安装"}
      </button>
    </div>
  );
}

// ─── 启动器项（带 Switch 切换 + 下载进度条） ────────────────

function LauncherItem({
  env,
  onDone,
}: {
  env: EnvCheckResult;
  onDone: () => void;
}) {
  const [region, setRegion] = useState<"cn" | "global">("cn");
  const [working, setWorking] = useState(false);
  const [msg, setMsg] = useState<string>();
  const [progress, setProgress] = useState<{ pct: number; downloaded_mb: number; total_mb: number; status: string } | null>(null);

  const current = region === "cn" ? env.launcher_cn : env.launcher_global;
  const anyReady = env.launcher_cn.ready || env.launcher_global.ready;
  const downloaded = !current.ready && current.detail?.includes("已下载");
  const downloading = progress?.status === "downloading";

  // 按钮状态
  let btnText = "下载";
  let btnIcon = <FaDownload size={10} />;
  if (current.ready) { btnText = "打开"; btnIcon = <FaRocket size={10} />; }
  else if (downloaded) { btnText = "安装"; btnIcon = <FaStore size={10} />; }
  else if (downloading) { btnText = "下载中"; btnIcon = <Spinner width={10} height={10} />; }

  // 轮询下载进度
  useEffect(() => {
    if (!downloading) return;
    const key = region === "cn" ? "launcher_cn" : "launcher_global";
    const timer = setInterval(async () => {
      try {
        const p = await getDownloadProgress(key);
        setProgress(p);
        if (p.status === "done") {
          clearInterval(timer);
          setProgress(null);
          setWorking(false);
          onDone();
          setMsg("下载完成");
        } else if (p.status === "error") {
          clearInterval(timer);
          setProgress(null);
          setWorking(false);
          setMsg(p.error || "下载失败");
        }
      } catch (_) {}
    }, 500);
    return () => clearInterval(timer);
  }, [downloading, region]);

  const handleClick = async () => {
    setWorking(true);
    setMsg(undefined);
    try {
      if (current.ready) {
        const label = region === "cn" ? "米哈游启动器" : "HoYoPlay";
        const res = await launchViaScript(region, "launcher", label, false);
        if (!res.success) setMsg(res.error || "启动失败");
        setWorking(false);
      } else if (downloaded) {
        const label = region === "cn" ? "米哈游启动器安装" : "HoYoPlay 安装";
        const res = await launchViaScript(region, "installer", `HoYoDeck · ${label}`, true);
        if (res.success) {
          setMsg("安装器已启动，请在 Steam 中完成安装");
        } else {
          setMsg(res.error || "启动安装器失败");
        }
        setWorking(false);
      } else {
        // 下载（异步，不阻塞）
        const key = region === "cn" ? "launcher_cn" : "launcher_global";
        setProgress({ pct: 0, downloaded_mb: 0, total_mb: 0, status: "downloading" });
        const res = await installComponent(key);
        if (!res.success) {
          setMsg(res.detail);
          setProgress(null);
          setWorking(false);
        }
        // 如果成功，轮询 useEffect 会接管
      }
    } catch (e) {
      setMsg(String(e));
      setProgress(null);
      setWorking(false);
    }
  };

  return (
    <div style={{
      padding: "8px 10px", borderRadius: 6,
      background: anyReady ? "rgba(76,175,80,.08)" : "rgba(255,152,0,.08)",
      border: `1px solid ${anyReady ? "rgba(76,175,80,.2)" : "rgba(255,152,0,.2)"}`,
    }}>
      {/* 标题行 + Switch */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {anyReady
            ? <FaCheckCircle color="#4caf50" size={14} />
            : <FaExclamationTriangle color="#ff9800" size={14} />
          }
          <span style={{ fontSize: 13, fontWeight: 600 }}>官方启动器</span>
        </div>
        <SegmentedSwitch
          options={[
            { label: "国服", value: "cn" },
            { label: "国际服", value: "global" },
          ]}
          value={region}
          onChange={(v) => { setRegion(v as "cn" | "global"); setMsg(undefined); setProgress(null); }}
        />
      </div>

      {/* 进度条 */}
      {downloading && progress && (
        <div style={{ marginBottom: 6 }}>
          <div style={{
            height: 6, borderRadius: 3, overflow: "hidden",
            background: "rgba(255,255,255,.1)",
          }}>
            <div style={{
              height: "100%", borderRadius: 3,
              width: `${Math.max(progress.pct, 2)}%`,
              background: "linear-gradient(90deg, #1a6dcc, #4fc3f7)",
              transition: "width 0.3s ease",
            }} />
          </div>
          <div style={{
            display: "flex", justifyContent: "space-between",
            fontSize: 10, opacity: 0.6, marginTop: 2,
          }}>
            <span>{progress.downloaded_mb} MB</span>
            <span>{progress.total_mb > 0 ? `${progress.pct}%` : "下载中..."}</span>
            <span>{progress.total_mb} MB</span>
          </div>
        </div>
      )}

      {/* 状态 + 按钮 */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 11, opacity: 0.7,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>{current.detail}</div>
          {msg && (
            <div style={{
              fontSize: 11, marginTop: 2,
              color: msg.includes("成功") || msg.includes("已存在") || msg.includes("启动") || msg.includes("完成") ? "#4caf50" : "#ff6b6b",
            }}>{msg}</div>
          )}
        </div>
        <button
          onClick={handleClick}
          disabled={working}
          style={{
            display: "flex", alignItems: "center", gap: 4,
            padding: "4px 12px", borderRadius: 5,
            border: "1px solid rgba(255,255,255,.15)",
            background: current.ready ? "rgba(76,175,80,.15)" : "rgba(255,255,255,.06)",
            color: current.ready ? "#4caf50" : "rgba(255,255,255,.8)",
            fontSize: 11, fontWeight: current.ready ? 600 : 400,
            cursor: working ? "wait" : "pointer",
            opacity: working ? 0.6 : 1, whiteSpace: "nowrap",
          }}
        >
          {btnIcon}
          {btnText}
        </button>
      </div>
    </div>
  );
}

// ─── 仪表盘主组件 ──────────────────────────────────────────

export function DashboardPanel() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [env, setEnv] = useState<EnvCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string>();
  const [envCollapsed, setEnvCollapsed] = useState(true);

  useEffect(() => {
    getDashboard().then(setDashboard).catch((e) => setError(String(e)));
    doCheck();
  }, []);

  const doCheck = async () => {
    setChecking(true);
    try {
      setEnv(await checkEnvironment());
    } catch (e) {
      setError(String(e));
    } finally {
      setChecking(false);
    }
  };

  // 未就绪项数：umu、proton、有一个启动器就通过
  const notReadyCount = env
    ? [env.umu, env.proton, env.steam_compat_dir].filter(i => !i.ready).length
      + (env.launcher_cn.ready || env.launcher_global.ready ? 0 : 1)
    : 0;

  return (
    <PanelSection>
      {/* 环境检查 — 可折叠 */}
      <PanelSectionRow>
        <div
          onClick={() => setEnvCollapsed(!envCollapsed)}
          style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "6px 0", cursor: "pointer", userSelect: "none",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {envCollapsed
              ? <FaChevronRight size={10} color="rgba(255,255,255,.5)" />
              : <FaChevronDown size={10} color="rgba(255,255,255,.5)" />
            }
            <span style={{ fontSize: 13, fontWeight: 600 }}>环境检查</span>
            {env && notReadyCount > 0 && (
              <span style={{
                fontSize: 10, padding: "1px 6px", borderRadius: 8,
                background: "rgba(255,152,0,.2)", color: "#ff9800",
              }}>{notReadyCount} 项待配置</span>
            )}
            {env && notReadyCount === 0 && (
              <FaCheckCircle color="#4caf50" size={12} />
            )}
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); doCheck(); }}
            disabled={checking}
            style={{
              display: "flex", alignItems: "center", gap: 4,
              padding: "3px 8px", borderRadius: 5,
              border: "1px solid rgba(255,255,255,.12)",
              background: "rgba(255,255,255,.05)",
              color: "rgba(255,255,255,.7)", fontSize: 11,
              cursor: checking ? "wait" : "pointer",
            }}
          >
            {checking ? <Spinner width={10} height={10} /> : <FaCog size={10} />}
            {checking ? "检查中..." : "刷新"}
          </button>
        </div>
      </PanelSectionRow>

      {/* 环境检查结果（展开时显示） */}
      {!envCollapsed && env && (
        <PanelSectionRow>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingBottom: 8 }}>
            <EnvItem item={env.umu} componentKey="umu" onDone={doCheck} />
            <EnvItem item={env.proton} componentKey="proton" onDone={doCheck} />
            <LauncherItem env={env} onDone={doCheck} />
            <EnvItem item={env.steam_compat_dir} componentKey="steam_compat_dir" onDone={doCheck} />
          </div>
        </PanelSectionRow>
      )}
      {!envCollapsed && checking && !env && (
        <PanelSectionRow>
          <div style={{ display: "flex", justifyContent: "center", padding: 16 }}><Spinner /></div>
        </PanelSectionRow>
      )}

      {/* 游戏统计 */}
      {dashboard && (
        <PanelSectionRow>
          <div style={{
            display: "flex", justifyContent: "space-around",
            padding: "12px 0", marginTop: 4,
            borderTop: "1px solid rgba(255,255,255,.08)",
          }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{dashboard.installed_count}</div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>{t("installedGames")}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{dashboard.game_count}</div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>{t("totalGames")}</div>
            </div>
          </div>
        </PanelSectionRow>
      )}

      {/* 清理按钮 */}
      <PanelSectionRow>
        <div style={{
          display: "flex", flexDirection: "column", gap: 6,
          padding: "8px 0", marginTop: 4,
          borderTop: "1px solid rgba(255,255,255,.08)",
        }}>
          <button
            onClick={() => {
              showModal(
                <ConfirmModal
                  strTitle="移除插件环境"
                  strDescription="将删除 UMU、Proton、Wine 前缀和下载的安装包。已安装的游戏数据也会被删除（因为它们在 Wine 前缀中）。Steam 快捷方式需要手动删除。确定继续？"
                  strOKButtonText="确定移除"
                  strCancelButtonText="取消"
                  onOK={async () => {
                    const res = await cleanupEnvironment();
                    doCheck();
                    if (res.success) {
                      showModal(
                        <ConfirmModal strTitle="清理完成" strDescription={res.detail} strOKButtonText="好的" />
                      );
                    }
                  }}
                />
              );
            }}
            style={{
              width: "100%",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              padding: "8px 12px", borderRadius: 6,
              border: "1px solid rgba(255,107,107,.3)",
              background: "rgba(255,107,107,.08)",
              color: "#ff6b6b", fontSize: 12, fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <FaTrash size={11} />
            移除插件环境
          </button>
          <button
            onClick={() => {
              showModal(
                <ConfirmModal
                  strTitle="移除环境和游戏"
                  strDescription="将删除所有插件数据（UMU、Proton、Wine 前缀、安装包）并移除所有 HoYoDeck 创建的 Steam 快捷方式。确定继续？"
                  strOKButtonText="确定全部移除"
                  strCancelButtonText="取消"
                  onOK={async () => {
                    const res = await cleanupAll();
                    doCheck();
                    if (res.success) {
                      showModal(
                        <ConfirmModal strTitle="清理完成" strDescription={res.detail} strOKButtonText="好的" />
                      );
                    }
                  }}
                />
              );
            }}
            style={{
              width: "100%",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              padding: "8px 12px", borderRadius: 6,
              border: "1px solid rgba(255,107,107,.5)",
              background: "rgba(255,107,107,.15)",
              color: "#ff6b6b", fontSize: 12, fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <FaTrash size={11} />
            移除环境 + 游戏
          </button>
        </div>
      </PanelSectionRow>

      {error && (
        <PanelSectionRow>
          <div style={{ color: "#ff6b6b", fontSize: 13, padding: 8 }}>{error}</div>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}
