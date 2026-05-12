# 小小桌面

这是一个只在 macOS 本地运行的窗口导航小工具，用于列出当前打开的窗口，并双击切换到对应窗口。

它使用 Python 3、Tkinter 和 `osascript` / AppleScript 调用 macOS System Events。不使用第三方 Python 包，不联网，不包含安装包、后台服务、数据库或菜单栏功能。

## 运行方式

已安装到本机后，可以直接打开：

```text
/Applications/小小桌面.app
```

也可以从 Finder 的 Applications 文件夹或 Spotlight 搜索 `小小桌面` 打开。

如果想从源码运行：

```bash
cd window-navigator
python3 window_navigator.py
```

窗口会按 App 折叠显示当前 macOS 上已打开窗口的名称，也会显示已经在运行但当前没有窗口的 App。点击右上角 `↻` 可以手动刷新列表；程序也会自动刷新。

点击 App 行左侧的展开符号可以展开/折叠它的窗口。展开后点击子项可以切换到对应窗口；Safari 会额外读取并显示标签页，点击标签页会切换到对应 Safari Tab。对于没有窗口的后台运行 App，主标题显示软件名称，副标题显示 `Open App · running, no window`。点击后会尝试激活 App 并调用 macOS 的 `reopen` 来打开一个窗口。

## 界面说明

当前版本仿照 macOS Reading List 小组件：无标题栏、半透明、置顶，列表先按 App 分组，展开后每行以窗口或标签页标题为主、App 名称为辅。按住顶部标题区域可以拖动位置，拖动右下角可以调整大小，按 Esc 或点击右上角 `×` 可以关闭。

读取窗口和切换窗口都在后台线程执行，避免 `osascript` 调用时卡住界面。

受 Tkinter 限制，它不是真正的 macOS 原生 Desktop Widget，也不能固定在 Finder 桌面层级里；它是一个轻量置顶浮窗。安装后的 `.app` 已设置为不显示 Dock 图标，打开后更像一个小面板。

## 权限说明

第一次运行可能需要开启 macOS 辅助功能权限：

System Settings → Privacy & Security → Accessibility

需要给运行它的程序授权，通常是：

- Terminal
- iTerm
- Python
- osascript

如果无法读取窗口或无法切换窗口：

1. 打开 System Settings → Privacy & Security → Accessibility
2. 给 Terminal / iTerm / Python 授权
3. 关闭并重新打开 Terminal
4. 重新运行 `python3 window_navigator.py`

## 已知限制

- 某些系统窗口可能无法读取。
- 某些 App 的窗口标题可能为空。
- 空标题窗口会显示为 `Untitled Window`，切换时主要依赖窗口序号。
- 已运行但没有窗口的 App 会显示软件名称，并在副标题里标记 `Open App`。
- 某些 App 不响应 macOS 的 `reopen` 事件，点击后可能只能激活 App，不能自动创建新窗口。
- 微信这类 App 会额外尝试 URL scheme、Dock 图标、菜单和常见快捷键来唤起窗口；如果它完全不响应这些入口，程序会至少激活 App 到前台。
- Safari 的 Tab 会通过 Safari AppleScript 读取并显示；其他浏览器的 Tab 通常不是独立系统窗口，当前不会逐个显示。
- 如果多个窗口名称完全相同，程序会优先使用 `window_index`，但仍可能切换到另一个同名窗口。
- 最小化窗口可能无法稳定切换。
- 纯 Python/Tkinter 不能做真正嵌入 Finder 桌面层级的原生 macOS 小组件；当前实现是置顶浮窗。
