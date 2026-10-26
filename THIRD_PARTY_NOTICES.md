# 来源与第三方许可

本项目以独立名称维护和分发。独立品牌不表示全部基础代码从零编写。

## 基础代码来源

窗口交互、托盘、可选 DeepSeek 对话与天气功能，基于 MIT 许可的
[1190fasheqi/dafeiyu-pet](https://github.com/1190fasheqi/dafeiyu-pet) 改造。
本地起点提交为 `5b0e018`。保留根目录 `LICENSE` 的原始 MIT 许可与版权声明。
原项目贡献者包括原维护者、[Cpanoe](https://github.com/Cpanoe)；其原有贡献记录见上游仓库。
本项目新增完整动漫动作、连续播放、简化陪伴页、提醒、通用自动避让、素材流式加载及发布流程。
本项目不是上游官方版本，也不代表上游作者。

## 分发依赖

| 组件 | 用途 | 许可/来源 |
|---|---|---|
| Python | 运行时 | PSF，随包附许可证 |
| PySide6 Essentials / Shiboken / Qt | 窗口、绘图、菜单 | 采用 LGPL v3 分发路径；其他组件许可见附带 notices |
| Requests / urllib3 / idna / charset-normalizer / certifi | 用户触发的可选网络功能 | 各自许可证随包附带 |
| psutil | 读取前台进程名称进行避让 | BSD，随包附许可证；不进行硬件监控 |
| PyInstaller | 构建 EXE | 构建工具，bootloader 具有分发例外；https://pyinstaller.org/en/stable/license.html |
| NumPy / OpenCV | 仅制作阶段补帧 | 不包含在桌宠运行包中 |

完整第三方文本和版本表位于安装目录 `_internal/third-party-licenses/`。
Qt/PySide 库以独立 DLL/PYD 动态链接提供，未修改，不进行加密或阻止替换；用户可用兼容版本替换、调试这些库。
对应项目源代码：[Qt 源码存档](https://download.qt.io/archive/qt/)、
[PySide 源码](https://code.qt.io/cgit/pyside/pyside-setup.git/)。以随包 `VERSIONS.txt` 匹配版本。
许可背景可查 [Qt for Python 官方许可说明](https://doc.qt.io/qtforpython-6/licenses.html)。

## 人物素材

当前示例为参考形象生成的动漫插画，采用内置图像生成工具制作；生成提示词保存在
`sprites-anime/unified-source/`。发布包不包含真人原始照片、聊天记录或联系人信息。
代码许可证不授予任何真实人物的姓名、肖像或身份使用权；使用自己的角色参考进行再创作时应确认相应授权。
