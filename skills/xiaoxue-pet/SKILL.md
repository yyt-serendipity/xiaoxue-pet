---
name: xiaoxue-pet
description: Create a lightweight Windows anime desktop pet from uploaded photos of a specified person, with consistent full-character animation, previews and a runnable project or EXE. Includes a standalone template. Also maintain 小薛同学桌宠 projects; not ChatGPT Work mode pets.
---

# 小薛同学桌宠 · 照片制作桌宠

用户提供人物照片后，将指定人物制作成统一画风的动漫桌宠，并交付预览和可运行文件。不是只返回提示词、三视图或换脸示意。支持已有项目维护；调用名 `$xiaoxue-pet` 保持兼容。

## 根据请求开始

- **照片制作新桌宠**：查看用户提供的照片，确定指定人物。多人照片中目标不明时只问人物位置；目标清楚时直接制作，不要求已有项目。没有新照片且用户没有指定沿用历史人物时，请用户提供照片。
- **维护现有项目**：先检查 README、适用 AGENTS.md 和当前差异；动作读 [artwork.md](references/artwork.md)，运行行为读 [runtime.md](references/runtime.md)，打包读 [release.md](references/release.md)。保留现有设置。
- 用户只要效果图时，做到角色预览即止；明确要桌宠或未限定为概念图时，继续完成动作、运行素材和交付。不要在完成一个头像后结束。

## 从照片交付

1. 读 [照片流程与素材契约](references/photo-workflow.md)。用明确的人物视觉特征锁定角色；不能把示例人物的帽子、眼镜、服装或性别当成所有用户的模板。
2. 使用可用的图像生成/编辑工具，以照片为人物参考生成完整人物基准。默认精细、柔和的 Q 版动漫，真实透明背景；用户指定画风优先。先查看本地输入图。所有后续动作同时引用人物基准，必要时引用照片；不能仅凭文字重新猜角色。
3. 依据形象基准自检后继续，不把每张图的确认都当成阻塞。提供可查看的基准预览；有新反馈及时吸收。重复脸型/衣服/比例漂移时修正对应原画，不能依赖光流掩盖。
4. 没有项目时，使用随 skill 附带的 `assets/runtime-template.zip`，通过 `scripts/bootstrap.py` 创建一个空目录中的独立项目。脚本只需 Python 标准库；模板不含真人照片、现有人物素材、Key 或虚拟环境，也不依赖作者电脑的路径。每个新项目使用独立应用 ID，避免覆盖已有桌宠的设置与安装位置。
5. 按素材契约逐组生成完整人物动作，存进新项目；记录提示词、每张输入图的用途、实际输出路径。不能只更新部分动作而留下其他人物的帧或图标。姿势和轮廓变化过大时补画过渡关键帧，不能通过加载更多大图解决。
6. 完成素材检查 → 离线编译 → 运行素材检查 → 预览；命令见流程文档。`scripts/validate_art.py` 检查透明度/帧完整性并生成角色图标；`scripts/render_preview.py` 用真实动画器采样生成可播放 HTML 与动作总览。查看实际 187/238 像素下的脸、脚底、抬手和收手。自动检查不证明人物相似度或动作自然度。
7. 在 Windows 上测试、打包、离线验证 EXE；其他系统交付素材、预览和可运行源码，明确 Windows 安装包尚未构建。完成 [发布检查](references/release.md)，默认只交付本地文件。不要自动安装、启用自启或上传 GitHub。

## 能力与边界

图像生成工具不可用时明确说明阻塞，保留已完成模板和素材清单；不要编程画占位人物或伪称照片转换完成。内置图像工具通常不需要桌宠聊天 Key；若可用 `imagegen` skill，遵循其工具流程，不能擅自切换为付费 API。桌宠内的 DeepSeek Key 只用于可选文字聊天。

运行时只加载 119/187/238 三档；完整人物逐帧、不拆肢体；相邻帧最多两张、混合缓存 2 MiB；隐藏暂停绘制并释放素材。图像生成、OpenCV、NumPy、原始大图均只用于制作，不进入运行包。参见 [运行约束](references/runtime.md)。

新桌宠的公开包默认不含输入真人照片、私人备注、API Key 和聊天记录。版权/来源说明不能因改名而移除。最终给出预览、源码/安装包/skill 文件链接、实际验证和未完成的限制；不能宣称“任何照片都能完全还原”或未经测量的内存/FPS。
