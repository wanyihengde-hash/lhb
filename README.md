# 龙虎榜 · 加速版

在海外用手机看东方财富龙虎榜总是加载不出来，这个仓库把数据「搬」到一个海外访问很快的地方。

手机打开：**https://wanyihengde-hash.github.io/lhb/**（Safari 里「分享 → 添加到主屏幕」，像 App 一样用）

```
东方财富数据接口 ──(本机计划任务定时拉取，失败自动重试)──> 仓库 docs/data/*.json
                                                            │ git push
手机浏览器 <──(GitHub Pages 全球 CDN，单页 + 一个 JSON)─────┘
```

- **定时同步**：Windows 计划任务 `lhb-sync`，交易日北京时间 16:30–21:30 每半小时一次，次日 09:10 再补一次。电脑开着才会跑，错过的会在开机后补跑。
- **页面很轻**：一个 HTML 加当天一个 JSON（gzip 后约 20KB）。原页面要从 30 多个域名加载资源，这里只有一个。
- **离线可看**：Service Worker 会缓存看过的数据，没网也能打开上次的内容。
- **直连兜底**：右上角「直连东财」让手机直接调东财接口拿最新一天的数据，适合电脑没开、还没同步的时候。
- **历史存档**：每天的数据都提交在 `docs/data/` 里，git 历史就是龙虎榜存档。

## 文件

| 路径 | 作用 |
| --- | --- |
| `scripts/fetch_lhb.py` | 拉数据（只用标准库），`--days N` 回补 N 个交易日 |
| `scripts/sync_local.ps1` | 计划任务调用：拉数据，有变化就提交并推送，日志在 `sync.log` |
| `scripts/install_task.ps1` | 注册计划任务（重复运行会覆盖旧的） |
| `docs/index.html` | 手机页面：筛选、排序、搜股票/营业部、展开看买卖前五 |
| `docs/sw.js` | 离线缓存 |
| `ci/update.yml` | 可选的云端同步（GitHub Actions），见下文 |

## 常用操作

- 立刻同步一次：`Start-ScheduledTask -TaskName lhb-sync`，或者直接运行 `scripts\sync_local.ps1`
- 停用：`Unregister-ScheduledTask -TaskName lhb-sync -Confirm:$false`
- 回补更多天：`python scripts/fetch_lhb.py --days 10`，然后提交推送

## 改成云端同步（不依赖电脑开机）

把 `ci/update.yml` 移到 `.github/workflows/update.yml` 并推送即可，之后 GitHub 会在云端按同样的时间表同步。
推送工作流文件需要 GitHub 登录带 `workflow` 权限（`gh auth refresh -s workflow`），也可以在 GitHub 网页上直接新建这个文件。
启用后记得停用本机计划任务，免得两边一起提交。

数据版权归东方财富，本项目仅供个人查看，不构成投资建议。
