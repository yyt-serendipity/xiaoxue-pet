# 照片到桌宠：制作与素材契约

## 输入与角色基准

一张清晰照片也可开始，2–5 张正面/侧面/全身图更有助于统一特征；不要把数量当硬性门槛。多人合照依赖用户指定的位置辨认目标，不做真人身份识别。不清楚的衣服下半身可以作协调的动漫设计，说明这是补充设计，不推断隐藏的个人信息。

在输出目录记录 `character-brief.md`：目标人物的位置、各图用途、脸型/发型/眼镜等可见特征、选定服装、配色、头身比与风格。不要把原始照片复制到源码或发布素材中。保留用户指定的人物性别表达及关键配饰，不套用小薛同学原角色的外观。

先生成透明全身中性站姿；这张基准会被所有动作引用。生成阶段保持高细节，运行阶段才缩小。参考图必须实际传给图像工具，不要只说“参考前一张”却没有关联图片。工具最多支持少量参考时优先基准、正面照片和当前动作原图。

提示词骨架（按人物改写，不机械复制）：

> 以参考图 A 中指定人物的可见特征建立角色，以基准图 B 的脸型、发型、服装细节、色彩和头身比为唯一动作角色。精细柔和 Q 版动漫，完整人物逐帧，真实透明背景，无地面/投影/文字/格线/装饰颗粒。生成下述姿势序列，按行从左到右排列；每格完整人物不截断，格间留透明空白，镜头/人物尺寸/脚底基线稳定。只改变动作要求涉及的姿势与表情，不更换脸、衣服或配饰。

## 新建独立项目

用实际 skill 目录替换 `<skill>`，用新项目路径替换 `<project>`；不是固定安装路径。

```powershell
python "<skill>/scripts/bootstrap.py" "<project>" --name "我的桌宠" --nickname "小伴"
cd "<project>"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install --target .asset-build-tools -r asset-build-requirements.txt
```

bootstrap 拒绝非空目标，不覆盖现有项目；应用 ID 默认由新项目路径生成，也可 `--app-id MyCompanion` 指定 ASCII 标识。新项目默认无预置人物，完成所有素材并编译后才可启动。模板是可编辑源码，不是运行时联网下载器。

## 原图契约

所有序列按行优先编号，从 0 开始。保存为 RGBA PNG，画面透明而非黑底/白底/棋盘背景。每个角色应有完整连贯的主体轮廓，避免分离的爱心粒子等干扰切图。当前检测器的大连通块阈值为 10,000 像素，建议图集长边至少 1536；小图需据实际分辨率调整阈值，不能硬补透明通道冒充合格。

| 相对 `sprites-anime/` 的文件 | 网格 | 顺序及含义 |
|---|---|---|
| `turnaround.png` | 3×1 | 正面、侧面、背面 |
| `blink-cycle.png` | 4×1 | 睁眼中性、半闭、闭眼、半睁；身体完全不动 |
| `walk-cycle.png` | 4×2 | 连贯 8 帧原地走路循环；0/7 相邻，不在图中整体平移 |
| `wave-cycle.png` | 3×2 | 中性、手抬到胸前、抬手张掌、手腕向外、手腕回摆、收至肩前 |
| `unified-source/style-reference.png` | 单张或参考表 | 当前角色基准，文件名固定，不沿用示例人物 |
| `unified-source/heart-finger.png` | 3×2 | 中性、低位抬手、半抬、接近完成、指尖比心完成、完成动作轻微变化 |
| `unified-source/heart-chest.png` | 3×2 | 同样 6 阶段，双手在胸前组成心形 |
| `unified-source/heart-overhead.png` | 3×2 | 同样 6 阶段，双臂举到头顶组成大心 |
| `unified-source/care.png` | 2×2 | 看书、坐着、睡觉、吃蛋糕 |
| `unified-source/expressions.png` | 2×2 | 害羞、开心、伸懒腰、被提起 |
| `unified-source/drink.png` | 2×2 | 手持杯低位、杯举到胸前、杯到嘴边、喝水 |

比心的第 5 帧不是“放下手”：播放器按 0→4，4↔5，再 4→0 收手。误画会导致突然放下又抬起。完整帧契约对齐 `animation.heart_sample` 和 `MotionClock.sample`。喝水和挥手也有反向收手路径。

人物太多导致细节下降时，每次生成一到两个完整角色，然后只进行确定性的裁剪、缩放、排版组成约定图集；不要放弃细节。新增原画必须用图像工具。切图/图集排版/缩小/图标封装不是重新绘制人物。

## 编译、预览与校验

```powershell
.\.venv\Scripts\python.exe "<skill>/scripts/validate_art.py" "<project>" --stage raw
.\.venv\Scripts\python.exe prepare_assets.py
.\.venv\Scripts\python.exe "<skill>/scripts/validate_art.py" "<project>" --stage prepared --make-icon
.\.venv\Scripts\python.exe "<skill>/scripts/render_preview.py" "<project>"
.\.venv\Scripts\python.exe -m unittest discover -p "test_*.py" -q
.\.venv\Scripts\python.exe main.py
```

检查输出的 `pet-preview.png`（素材总览）和 `pet-preview.html`（实际动画器采样的循环预览），明确它们是素材/动画预览而不是桌面实拍。运行主程序前清除测试用 `QT_QPA_PLATFORM=offscreen`。不打开或截图用户隐私窗口。

`prepare_assets.py` 会一起生成比心与走路/挥手/喝水中间帧和对应清单。总览动画采用较低采样率，不能用它判断 20ms 调度下的丝滑程度。维护已有动作时，可将修改前的 animation.py 保存在本地备份，再运行 `scripts/compare_motion.py --baseline <备份路径>` 导出实际动画器 50Hz 采样对比；备份源码不放进公开包。对比的单进程渲染开销不是整个桌宠或游戏性能。

编译器当前含原角色校准值：`prepare_unified_art.py` 的 crown_offset 25/29、主体相对高度和 `animation.load_frames_raw` 的帽沿锚点。对无帽子、不同发型、长裙、抬高手臂的新角色，必须查看脚底与头部位置并重新校准，不能把数值当通用人物规格。可以修改完整图的平移/缩放和动作时间线，不改为分层肢体。

素材检查能发现缺图、缺帧、透明度和尺寸错误；脸型相似、衣纹连贯、手指形态、动作自然度仍需视觉检查。光流中间帧在手部遮挡处可能产生残影，应该重做临近关键帧或增加真实过渡姿势，再调整插值，而非承诺自动修好。

## 交付

Windows：安装构建依赖后运行 `scripts/build_release.py`、`scripts/verify_release.py`。交付默认路径 `.release/` 内的安装版和免安装 ZIP，以及人物基准、预览与源码。新项目的 artifact 文件名前缀为 bootstrap 写入的独立应用 ID。

公开源码自行采用白名单：必要代码/许可证/生成的动漫素材，不含输入照片、character-brief 中的私人备注、配置、环境、日志或 `.release`。模板没有直接沿用原项目的发布导出脚本，因为那个脚本依赖原项目文档与素材目录。

没有图像工具或 Windows 编译条件时，报告具体缺失部分；不将模板初始化、演示素材测试或旧 EXE 当作新人物桌宠已完成。生成可能需要多轮，skill 本身不是照片转换模型，也不是一键云端服务。
