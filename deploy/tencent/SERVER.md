# 服务器存档

> 给任何接手这个项目的对话看。不用再问一遍机器在哪、装到哪了。
> 最后更新：2026-10-28

## 实例

| 项 | 值 |
| --- | --- |
| 云厂商 | 阿里云 |
| 产品 | 云服务器 ECS（免费试用，按量付费） |
| 实例 ID | `i-bp13nh742c64vnf2lzfd` |
| 实例名 | `iZ2c64vnf2izfdZ` |
| 地域 | 华东1（杭州） |
| 规格 | `ecs.e-c1m2.large`，2 核 4 GiB（经济型 e） |
| 系统盘 | 40 GiB ESSD Entry |
| 公网 IP | `120.26.27.49` |
| 私网 IP | `172.20.90.206` |
| 公网带宽 | 100 Mbps 峰值，**按使用流量**计费，每月 20 GB 免费流量 |
| 操作系统 | **Ubuntu 24.04 64 位**（2026-10-28 从 Windows Server 2022 换过来的） |
| 安全组 | 入方向只放 22；**6099、8080 没放通**，WebUI 走 SSH 隧道 |
| 登录 | `root` + 密码。密码不进仓库，忘了就在控制台「重置密码」 |

## 试用额度

- 有效期：2026-10-28 21:00 → 2027-01-28 21:00
- 额度：300 元，只抵扣按量付费的 ECS 实例和系统盘
- 单价：0.254 元/小时；跑满 30 天约 185 元，额度够
- **不用了要「释放实例」**，只关机照样按量计费
- 试用 ECS 不支持备案（本项目不开网站，无影响）

## 当前进度

- [x] 开实例、Windows 换 Ubuntu 24.04
- [ ] 上传代码包 `dist/qqbot-deploy.tar.gz`
- [ ] `bootstrap.sh` 装依赖（xvfb / venv / QQ / NapCat）
- [ ] 扫码登录机器人 QQ
- [ ] 配反向 WS + 挂 systemd
- [ ] 验收 `curl 127.0.0.1:8080/healthz` → `bots:1`

## 部署路线

**Linux 原生**：xvfb + 官方安装器装 QQ/NapCat，装在 `/root/Napcat`。
不是 Docker，也不用仓库里 `tools/` 那份 Windows 版 NapCat。

| 文件 | 作用 |
| --- | --- |
| `deploy/tencent/README.md` | 全流程，含腾讯云/阿里云差异 |
| `deploy/tencent/bootstrap.sh` | 装依赖 + swap + venv + QQ/NapCat |
| `deploy/tencent/qqbot.service` | 机器人 systemd |
| `deploy/tencent/napcat.service` | NapCat systemd（安装器自带服务时不要装这个） |
| `deploy/tencent/pack.ps1` | 本地打包 |
| `deploy/tencent/remote.py` | 密码 SSH 跑命令 / 传包（备用） |

标准命令：

```bash
# 本地
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\tencent\pack.ps1
scp .\dist\qqbot-deploy.tar.gz root@120.26.27.49:~/

# 服务器
mkdir -p /opt/qqbot
tar -xzf ~/qqbot-deploy.tar.gz -C /opt/qqbot
sed -i 's/^AI_IMAGE_OCR=.*/AI_IMAGE_OCR=false/' /opt/qqbot/.env
bash /opt/qqbot/deploy/tencent/bootstrap.sh
xvfb-run -a /root/Napcat/opt/QQ/qq --no-sandbox -q <机器人QQ号>
```

## 本机环境

- 项目：`E:\qqbot`，Windows
- Python：`.venv` 3.12.5
- 打包产物：`dist\qqbot-deploy.tar.gz`（约 2.3 MB，不含 `data/`）
- 模型：中转站 `https://cn3.heilovehei.com/v1`，模型 `deepseek-v4.1-flash`
- `.env` 里已有真的 `DEEPSEEK_API_KEY` 和 `ONEBOT_ACCESS_TOKEN`，**别提交、别外传**
- 机器人 QQ：见 `.env` 的 `AI_FISH_QQ`（管理员）、实际登录号是另一个小号

## 已知坑

| 坑 | 说明 |
| --- | --- |
| Linux 没有 NapCat OCR | `AI_IMAGE_OCR` 必须 `false`，看图靠 `AI_VISION_MODEL` |
| 40G 盘选不了 Windows 镜像 | 阿里云要求系统盘 > 40 GiB 才能选 Windows |
| 换系统会清盘 | 这台没数据，换完公网 IP 不变 |
| 机房 IP 登 QQ 有风控 | 用小号，掉线重扫，别频繁换 IP |
| `tools/` 是 win64 | Linux 上跑不了，别往服务器传 |
| 试用到期数据只留 1–15 天 | 到期前 `scp` 回 `data/bot.db` 和 `.env` |
| pip 装 `paramiko` 报 `No matching distribution` | 清华源那时不通，换 `-i https://mirrors.aliyun.com/pypi/simple/` 装上了（5.1.0） |

## 密码放哪

不写在本文档里（会被 git 记）。放这两个地方之一：

- 本机 `deploy/tencent/server.secret.md`（已在 `.gitignore`）
- 控制台「重置密码」随时能改
