<!-- markdownlint-disable MD024 MD026 MD031 MD033 MD036 MD041 -->
<div align="center">
  <img src="https://raw.githubusercontent.com/Agnes4m/nonebot_plugin_l4d2_server/main/image/logo.png" width="180" height="180"  alt="AgnesDigitalLogo">
  <br>
  <p><img src="https://s2.loli.net/2022/06/16/xsVUGRrkbn1ljTD.png" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot_plugin_bilifan

_✨ 自动 b 站粉丝牌 ✨_

<a href="https://github.com/Agnes4m/nonebot_plugin_bilifan/stargazers">
        <img alt="GitHub stars" src="https://img.shields.io/github/stars/Agnes4m/nonebot_plugin_bilifan" alt="stars">
</a>
<a href="https://github.com/Agnes4m/nonebot_plugin_bilifan/issues">
        <img alt="GitHub issues" src="https://img.shields.io/github/issues/Agnes4m/nonebot_plugin_bilifan" alt="issues">
</a>
<a href="https://jq.qq.com/?_wv=1027&k=HdjoCcAe">
        <img src="https://img.shields.io/badge/QQ%E7%BE%A4-399365126-orange?style=flat-square" alt="QQ Chat Group">
</a>
<a href="https://pypi.python.org/pypi/nonebot_plugin_bilifan">
        <img src="https://img.shields.io/pypi/v/nonebot_plugin_bilifan.svg" alt="pypi">
</a>
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">
    <img src="https://img.shields.io/badge/nonebot-2.0.0-red.svg" alt="NoneBot">
</div>

## 最新说明~~叔叔不要麻辣~~

- <font color=#ff0000>2026.03.15 本次更新配置文件有变更，需要使用【更新插件配置】指令同步最新配置</font>
- 由于 b 站修改规则，每日粉丝牌亲密度上限为 **30**，牌子默认停止打卡等级调整为 **120 级**
- 登录后支持自动写入/更新 `refresh_token`，过期时将自动刷新 `access_key`，刷新失败才标记为过期
- 支持同一 B 站账号重复登录时自动更新 `access_key`，不同账号则自动新增
- 新增观看直播间顺序优先级配置（`WATCHLIVE_ORDER`）
- 新增活动签到功能（`ACTIVITY_SIGNIN`）
- 新增定时任务随机延时功能（`RANDOM_DELAY`）
- 新增 `LIKE_CHECK_LIGHT` 配置，可仅对未点亮粉丝牌进行点赞
- 新增 `LIKE_NUM` / `DANMAKU_NUM` 配置，可自定义点赞/弹幕发送数量
- 支持 `更新插件配置` 指令，一键批量更新所有用户配置文件至最新模板（保留原有配置值）
- alconna 支持替换 saa 支持

## 配置说明

启动一次插件，在 bot 路径下 `data/bilifan` 文件夹内，按需求修改 `users.yaml` 文件。
运行跨平台使用，支持 alconna 下所有适配器。

### users.yaml 配置项说明

#### 账号配置（USERS 列表）

| 字段            | 说明                                                          | 默认值  |
| --------------- | ------------------------------------------------------------- | ------- |
| `access_key`    | B 站登录凭证，扫码登录后自动填写                              | 必填    |
| `bili_uid`      | B 站用户 UID，登录后自动填写                                  | `0`     |
| `bili_name`     | B 站用户昵称，登录后自动填写                                  | `""`    |
| `refresh_token` | 刷新令牌，登录后自动填写，用于自动刷新 access_key             | `""`    |
| `white_uid`     | 白名单 UID，填写后只打卡这些用户（逗号分隔），填 `0` 则不限制 | `0`     |
| `banned_uid`    | 黑名单 UID，填写后跳过这些用户（逗号分隔），填 `0` 则不限制   | `0`     |
| `is_expired`    | 登录是否过期，过期后自动跳过，重新登录后自动清除              | `false` |

> 支持无限账号，同一 B 站用户再次登录会更新 `access_key`，不同用户则新增。
> 若执行任务时登录已过期，会先尝试用 `refresh_token` 自动刷新，刷新失败才标记为过期。

#### 全局行为配置

| 配置项             | 说明                                                                                             | 默认值       |
| ------------------ | ------------------------------------------------------------------------------------------------ | ------------ |
| `WRITE_LOG_FILE`   | 是否写入日志文件。`True` 写入默认目录，填绝对路径写入指定位置，`False` 不写入                    | `False`      |
| `CRON`             | cron 表达式，格式：`分 时 * * *`，不填则不启用内置定时器                                         | `0 0 * * *`  |
| `STOPWATCHINGTIME` | 限制单轮直播任务的最大运行时间。支持 `'HH:mm:ss'` 格式（到达该时刻停止）或秒数格式，不填则不生效 | `"00:00:00"` |
| `RANDOM_DELAY`     | 定时任务随机延时最大秒数，每个用户启动时随机延时 1 到该值的秒数，`0` 为不延时                    | `0`          |
| `LEVEN`            | 牌子停止打卡等级，达到此等级后不再计入每日任务                                                   | `120`        |

#### 点赞配置

| 配置项             | 说明                                                                                        | 默认值 |
| ------------------ | ------------------------------------------------------------------------------------------- | ------ |
| `ASYNC`            | 异步执行点赞，`1` 开启（同时点赞所有直播间），`0` 关闭（逐个同步点赞）；开启后不支持点赞 CD | `0`    |
| `LIKE_CD`          | 同步点赞间隔时间（秒），`0` 则不点赞                                                        | `3`    |
| `LIKE_NUM`         | 点赞次数                                                                                    | `30`   |
| `LIKE_CHECK_LIGHT` | 仅对未点亮的粉丝牌进行点赞，`1` 开启，`0` 关闭                                              | `0`    |

#### 弹幕配置

| 配置项                | 说明                                                               | 默认值 |
| --------------------- | ------------------------------------------------------------------ | ------ |
| `DANMAKU_CD`          | 弹幕间隔时间（秒），`0` 则不发弹幕打卡                             | `6`    |
| `DANMAKU_NUM`         | 每个直播间发送弹幕次数                                             | `10`   |
| `DANMAKU_CHECK_LIGHT` | 仅对未点亮的粉丝牌发送弹幕，`1` 开启，`0` 关闭                     | `1`    |
| `DANMAKU_CHECK_LIVE`  | 正在直播的用户不发送弹幕，`1` 开启，`0` 关闭                       | `1`    |
| `DANMAKU_CHECK_LEVEL` | 发送弹幕是否包含已达停止打卡等级的粉丝牌，`1` 开启，`0` 关闭       | `1`    |
| `WEARMEDAL`           | 发弹幕时自动佩戴当前房间的粉丝牌，避免等级禁言，`1` 开启，`0` 关闭 | `0`    |

#### 观看直播配置

| 配置项            | 说明                                                                                                 | 默认值 |
| ----------------- | ---------------------------------------------------------------------------------------------------- | ------ |
| `WATCHINGLIVE`    | 每日每直播间观看时长（分钟），`0` 则关闭观看任务                                                     | `25`   |
| `WATCHINGALL`     | 是否同时观看已达停止打卡等级的直播间（每个 5 分钟），保持粉丝牌持续点亮，`1` 开启，`0` 关闭          | `0`    |
| `WHACHASYNER`     | 是否异步观看直播间，`1` 开启（同时观看全部直播间），`0` 关闭（逐个同步观看）                         | `0`    |
| `WATCHLIVE_ORDER` | 观看直播间顺序优先级：`0` 随机，`1` 高等级优先，`2` 低等级优先，`3` 即将升级优先，`4` 不即将升级优先 | `0`    |

#### 其他任务配置

| 配置项            | 说明                                        | 默认值 |
| ----------------- | ------------------------------------------- | ------ |
| `SIGNINGROUP`     | 应援团签到 CD（秒），`0` 则不执行应援团签到 | `0`    |
| `ACTIVITY_SIGNIN` | 活动签到 CD（秒），`0` 则不执行活动签到     | `2`    |

## 指令

| 指令                           | 权限       | 说明                                                                   |
| ------------------------------ | ---------- | ---------------------------------------------------------------------- |
| `b站登录`                      | 所有人     | 返回 B 站二维码，扫码登录并绑定账号                                    |
| `删除登录信息`                 | 所有人     | 删除当前用户的登录信息和绑定                                           |
| `开始刷牌子`                   | 所有人     | 立即执行一次粉丝牌任务                                                 |
| `自动刷牌子`                   | 所有人     | 添加定时任务（依赖 `CRON` 配置）                                       |
| `取消自动刷牌子`               | 所有人     | 取消当前用户的定时任务                                                 |
| `删除全部定时任务`             | 超级管理员 | 删除全部定时任务                                                       |
| `b站删除配置`                  | 超级管理员 | 删除全部配置文件（初始化）                                             |
| `更新插件配置` / `b站更新配置` | 超级管理员 | 将所有用户配置文件批量更新至最新模板，保留原有配置值，并自动备份旧文件 |

## 🙈 其他

- 本项目仅供学习使用，请勿用于商业用途，喜欢该项目可以 Star 或者提供 PR
- [爱发电](https://afdian.net/a/agnes_digital)
- [GPL-3.0 License](https://github.com/Agnes4m/nonebot_plugin_bilifan/blob/main/LICENSE) ©[@Agnes4m](https://github.com/Agnes4m)

## 🌐 感谢

- [新 B 站粉丝牌助手 - XiaoMiku01](https://github.com/XiaoMiku01/fansMedalHelper) - 源代码来自于他
- [新 B 站粉丝牌助手 - cyb233](https://github.com/cyb233/fansMedalHelper) - 改进代码来自于他
