// Built using Windows' .NET Framework compiler; no downloaded installer framework.
using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("小薛同学桌宠安装程序")]
[assembly: AssemblyProduct("小薛同学桌宠")]
[assembly: AssemblyVersion("1.0.5.0")]
[assembly: AssemblyFileVersion("1.0.5.0")]

static class Product {
    public const string Name = "小薛同学桌宠";
    public const string Exe = "XiaoxuePet.exe";
    public const string Id = "xiaoxue-pet-install-v1-403369d4";
    public const string Marker = ".xiaoxue-install";
    public const string RegistryPath = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\XiaoxuePet";
    public static string DefaultPath { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "XiaoxuePet"); } }

    public static string InstalledPath {
        get {
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(RegistryPath)) {
                string value = key == null ? null : key.GetValue("InstallLocation") as string;
                if (!String.IsNullOrWhiteSpace(value) && File.Exists(Path.Combine(value, Marker))) {
                    Owned(value); return Path.GetFullPath(value);
                }
            }
            return null;
        }
    }
    public static string NormalizeInstallPath(string value) {
        string expanded = Environment.ExpandEnvironmentVariables((value ?? "").Trim());
        if (expanded.Length < 3 || !Char.IsLetter(expanded[0]) || expanded[1] != ':' || (expanded[2] != '\\' && expanded[2] != '/'))
            throw new IOException("请输入本地磁盘的完整目录，例如 D:\\Apps\\XiaoxuePet。");
        string root = Path.GetFullPath(expanded).TrimEnd('\\', '/');
        if (root.Length <= 3 || root.Substring(2).Contains(':')) throw new IOException("请选择一个专用文件夹，不要直接安装到磁盘根目录。");
        string windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows).TrimEnd('\\');
        if (String.Equals(root, windows, StringComparison.OrdinalIgnoreCase) || root.StartsWith(windows + "\\", StringComparison.OrdinalIgnoreCase))
            throw new IOException("请选择 Windows 系统目录之外的文件夹。");
        for (string part = root; part != null; part = Path.GetDirectoryName(part))
            if (Directory.Exists(part) && (File.GetAttributes(part) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("请选择实际文件夹，不要使用目录链接。");
        return root;
    }
    public static void ValidateUpgradeLocation(string root, string installed) {
        if (installed != null && !String.Equals(NormalizeInstallPath(root), NormalizeInstallPath(installed), StringComparison.OrdinalIgnoreCase))
            throw new IOException("已安装在 " + installed + "。可在原目录升级；如需迁移，请先卸载旧程序，个人设置会保留。");
    }

    public static string SafePath(string root, string relative) {
        string fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar);
        string path = Path.GetFullPath(Path.Combine(fullRoot, relative));
        if (!path.StartsWith(fullRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new IOException("文件路径超出安装目录。");
        for (string check = Path.GetDirectoryName(path); check != null && check.Length >= fullRoot.Length; check = Path.GetDirectoryName(check))
            if (Directory.Exists(check) && (File.GetAttributes(check) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("安装目录不能含有目录链接。");
        return path;
    }
    public static HashSet<string> Owned(string root) {
        string marker = SafePath(root, Marker);
        if (!File.Exists(marker)) return new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        string[] lines = File.ReadAllLines(marker);
        if (lines.Length == 0 || lines[0] != Id) throw new IOException("此目录不属于小薛同学桌宠。");
        foreach (string file in lines.Skip(1)) SafePath(root, file);
        return new HashSet<string>(lines.Skip(1), StringComparer.OrdinalIgnoreCase);
    }
    public static void EnsureClosed(string root) {
        string exe = Path.Combine(Path.GetFullPath(root), Exe);
        foreach (Process p in Process.GetProcessesByName("XiaoxuePet")) {
            try { if (String.Equals(p.MainModule.FileName, exe, StringComparison.OrdinalIgnoreCase)) throw new IOException("请先从托盘退出小薛同学桌宠，再重试。"); }
            catch (System.ComponentModel.Win32Exception) { }
            finally { p.Dispose(); }
        }
    }
    public static void Shortcut(string path, string root, bool remove) {
        if (remove && !File.Exists(path)) return;
        dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
        dynamic link = shell.CreateShortcut(path);
        string exe = Path.Combine(root, Exe);
        if (remove) {
            if (String.Equals((string)link.TargetPath, exe, StringComparison.OrdinalIgnoreCase)) File.Delete(path);
        } else {
            link.TargetPath = exe; link.WorkingDirectory = root;
            link.IconLocation = exe + ",0"; link.Description = Name; link.Save();
        }
    }
    public static void Register(string root, bool desktop) {
        string start = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), Name + ".lnk");
        Shortcut(start, root, false);
        if (desktop) Shortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), Name + ".lnk"), root, false);
        using (RegistryKey key = Registry.CurrentUser.CreateSubKey(RegistryPath)) {
            key.SetValue("DisplayName", Name); key.SetValue("DisplayVersion", "1.0.5");
            key.SetValue("InstallLocation", root); key.SetValue("DisplayIcon", Path.Combine(root, Exe));
            key.SetValue("UninstallString", "\"" + Path.Combine(root, "Uninstall.exe") + "\"");
            key.SetValue("NoModify", 1, RegistryValueKind.DWord); key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
        }
    }
    public static void Uninstall(string root, bool integration) {
        root = Path.GetFullPath(root); EnsureClosed(root);
        HashSet<string> owned = Owned(root);
        if (!File.Exists(SafePath(root, Marker))) throw new IOException("缺少安装清单，未删除任何文件。");
        foreach (string file in owned) { string path = SafePath(root, file); if (File.Exists(path)) File.Delete(path); }
        File.Delete(SafePath(root, Marker));
        // Remove only empty directories reachable from recorded package files.
        var directories = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (string file in owned) {
            string d = Path.GetDirectoryName(SafePath(root, file));
            while (d != null && d.StartsWith(root, StringComparison.OrdinalIgnoreCase) && d.Length >= root.Length) {
                directories.Add(d); if (d == root) break; d = Path.GetDirectoryName(d);
            }
        }
        foreach (string d in directories.OrderByDescending(p => p.Length))
            if (Directory.Exists(d) && !Directory.EnumerateFileSystemEntries(d).Any()) Directory.Delete(d);
        if (integration) {
            foreach (string folder in new [] { Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), Environment.GetFolderPath(Environment.SpecialFolder.Programs) })
                Shortcut(Path.Combine(folder, Name + ".lnk"), root, true);
            Shortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Startup), "XiaoxuePet.lnk"), root, true);
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(RegistryPath)) {
                if (key != null && String.Equals((string)key.GetValue("InstallLocation"), root, StringComparison.OrdinalIgnoreCase)) {
                    key.Close(); Registry.CurrentUser.DeleteSubKeyTree(RegistryPath, false);
                }
            }
        }
    }
}

#if !UNINSTALLER
static class Package {
    public static void Install(string root, bool integration, bool desktop, Action<int> progress = null) {
        root = Product.NormalizeInstallPath(root);
        if (integration) Product.ValidateUpgradeLocation(root, Product.InstalledPath);
        Product.EnsureClosed(root);
        var oldFiles = Product.Owned(root);
        if (Directory.Exists(root) && Directory.EnumerateFileSystemEntries(root).Any() && !File.Exists(Product.SafePath(root, Product.Marker)))
            throw new IOException("这个文件夹已有其他文件。请选择空文件夹，或在其中新建桌宠专用文件夹。");
        Directory.CreateDirectory(root);
        string backup = Path.Combine(Path.GetTempPath(), "XiaoxueBackup-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(backup);
        var written = new List<string>(); var replaced = new List<string>();
        try {
            using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
            using (ZipArchive zip = new ZipArchive(stream, ZipArchiveMode.Read)) {
                int count = 0;
                foreach (ZipArchiveEntry entry in zip.Entries) {
                    if (String.IsNullOrEmpty(entry.Name)) continue;
                    string relative = entry.FullName.Replace('/', Path.DirectorySeparatorChar);
                    string dest = Product.SafePath(root, relative);
                    if (File.Exists(dest)) {
                        if (!oldFiles.Contains(relative)) throw new IOException("目标位置存在非安装程序管理的文件：" + relative);
                        string copy = Product.SafePath(backup, relative); Directory.CreateDirectory(Path.GetDirectoryName(copy));
                        File.Copy(dest, copy, false); replaced.Add(relative);
                    }
                    Directory.CreateDirectory(Path.GetDirectoryName(dest)); written.Add(relative);
                    using (Stream input = entry.Open()) using (FileStream output = File.Create(dest)) input.CopyTo(output);
                    count++; if (progress != null) progress(count * 100 / Math.Max(1, zip.Entries.Count));
                }
            }
            var all = new HashSet<string>(oldFiles, StringComparer.OrdinalIgnoreCase); all.UnionWith(written);
            File.WriteAllLines(Product.SafePath(root, Product.Marker), new [] { Product.Id }.Concat(all.OrderBy(p => p)).ToArray());
            if (integration) Product.Register(root, desktop);
        } catch {
            foreach (string file in written) { string path = Product.SafePath(root, file); if (File.Exists(path)) File.Delete(path); }
            foreach (string file in replaced) File.Copy(Product.SafePath(backup, file), Product.SafePath(root, file), true);
            if (oldFiles.Count > 0) File.WriteAllLines(Product.SafePath(root, Product.Marker), new [] { Product.Id }.Concat(oldFiles).ToArray());
            else if (File.Exists(Product.SafePath(root, Product.Marker))) File.Delete(Product.SafePath(root, Product.Marker));
            throw;
        } finally {
            // The backup contains only explicitly recorded copies, never arbitrary user trees.
            foreach (string file in replaced) { string path = Product.SafePath(backup, file); if (File.Exists(path)) File.Delete(path); }
            foreach (string dir in Directory.GetDirectories(backup, "*", SearchOption.AllDirectories).OrderByDescending(p => p.Length))
                if (!Directory.EnumerateFileSystemEntries(dir).Any()) Directory.Delete(dir);
            if (!Directory.EnumerateFileSystemEntries(backup).Any()) Directory.Delete(backup);
        }
    }
}

static class Shapes {
    public static GraphicsPath Round(RectangleF r, float radius) {
        float d = radius * 2; var path = new GraphicsPath();
        path.AddArc(r.X, r.Y, d, d, 180, 90); path.AddArc(r.Right-d, r.Y, d, d, 270, 90);
        path.AddArc(r.Right-d, r.Bottom-d, d, d, 0, 90); path.AddArc(r.X, r.Bottom-d, d, d, 90, 90);
        path.CloseFigure(); return path;
    }
}
class SoftButton : Button {
    public bool Primary;
    bool hover;
    public SoftButton() { FlatStyle = FlatStyle.Flat; FlatAppearance.BorderSize = 0; Cursor = Cursors.Hand; SetStyle(ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer, true); }
    protected override void OnMouseEnter(EventArgs e) { hover = true; Invalidate(); base.OnMouseEnter(e); }
    protected override void OnMouseLeave(EventArgs e) { hover = false; Invalidate(); base.OnMouseLeave(e); }
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.Clear(Parent.BackColor); e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        Color fill = Primary ? Color.FromArgb(49, 77, 99) : Color.FromArgb(237, 241, 244);
        if (hover && Enabled) fill = Primary ? Color.FromArgb(64, 94, 117) : Color.FromArgb(224, 232, 237);
        if (!Enabled) fill = Color.FromArgb(220, 226, 230);
        using (var shape = Shapes.Round(new RectangleF(0, 0, Width-1, Height-1), Height*.23f))
        using (var brush = new SolidBrush(fill)) e.Graphics.FillPath(brush, shape);
        TextRenderer.DrawText(e.Graphics, Text, Font, ClientRectangle, Enabled ? (Primary ? Color.White : Color.FromArgb(49,77,99)) : Color.Gray, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
        if (Focused && ShowFocusCues) ControlPaint.DrawFocusRectangle(e.Graphics, Rectangle.Inflate(ClientRectangle, -5, -5));
    }
}
class PathBox : Panel {
    public PathBox() { DoubleBuffered = true; BackColor = Color.White; }
    protected override void OnPaint(PaintEventArgs e) {
        base.OnPaint(e); e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        using (var shape = Shapes.Round(new RectangleF(.5f, .5f, Width-1, Height-1), Height*.22f))
        using (var pen = new Pen(ContainsFocus ? Color.FromArgb(87,121,146) : Color.FromArgb(214,223,229))) e.Graphics.DrawPath(pen, shape);
    }
}
class ProgressTrack : Control {
    int value;
    public int Value { get { return value; } set { this.value = Math.Max(0, Math.Min(100, value)); Invalidate(); } }
    public ProgressTrack() { DoubleBuffered = true; }
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.Clear(Color.FromArgb(235,240,243));
        using (var brush = new SolidBrush(Color.FromArgb(87,121,146))) e.Graphics.FillRectangle(brush, 0, 0, Width*value/100, Height);
    }
}
class SetupWindow : Form {
    bool completed, busy;
    readonly SoftButton install = new SoftButton { Primary = true };
    readonly SoftButton browse = new SoftButton();
    readonly SoftButton cancel = new SoftButton();
    readonly TextBox location = new TextBox();
    readonly CheckBox desktop = new CheckBox();
    readonly CheckBox launch = new CheckBox();
    readonly Label status = new Label();
    readonly ProgressTrack progress = new ProgressTrack();
    readonly PictureBox avatar = new PictureBox();
    readonly Color ink = Color.FromArgb(40,55,67), muted = Color.FromArgb(112,126,137);
    Label Caption(string text, int x, int y, int w, int h, float size, bool bold, Color color) {
        return new Label { Text = text, Location = new Point(x,y), Size = new Size(w,h), Font = new Font("Microsoft YaHei UI",size,bold ? FontStyle.Bold : FontStyle.Regular), ForeColor = color, BackColor = Color.Transparent };
    }
    public SetupWindow(bool preview = false) {
        SuspendLayout(); AutoScaleDimensions = new SizeF(96,96); AutoScaleMode = AutoScaleMode.Dpi;
        Text = Product.Name + " · 安装"; ClientSize = new Size(760,480);
        FormBorderStyle = FormBorderStyle.FixedSingle; MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen; BackColor = Color.FromArgb(253,253,252);
        Font = new Font("Microsoft YaHei UI",9.5f); ForeColor = ink;
        Icon = Icon.ExtractAssociatedIcon(Assembly.GetExecutingAssembly().Location);
        var art = new Panel { Location = Point.Empty, Size = new Size(238,480), BackColor = Color.FromArgb(233,240,243) };
        art.Controls.Add(Caption("你的桌面伙伴",30,30,185,26,10,false,Color.FromArgb(87,112,131)));
        avatar.Location = new Point(24,82); avatar.Size = new Size(190,258); avatar.SizeMode = PictureBoxSizeMode.Zoom;
        using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("avatar.png")) {
            if (stream != null) using (Image source = Image.FromStream(stream)) avatar.Image = new Bitmap(source);
            else avatar.Image = Icon.ToBitmap();
        }
        art.Controls.Add(avatar);
        art.Controls.Add(Caption("轻轻陪着你。",30,368,200,36,18,true,ink));
        art.Controls.Add(Caption("也给专注留一点空间",31,411,195,24,9,false,muted));
        Controls.Add(art);
        Controls.Add(Caption("让陪伴，住进桌面",274,39,450,44,22,true,ink));
        Controls.Add(Caption(Product.Name + "  /  1.0.5",276,94,448,26,10,false,muted));
        Controls.Add(Caption("安装位置",274,157,400,24,10,true,ink));
        var path = new PathBox { Location = new Point(274,192), Size = new Size(346,44) };
        location.BorderStyle = BorderStyle.None; location.Location = new Point(12,12); location.Size = new Size(322,24);
        location.BackColor = Color.White; location.ForeColor = ink; location.AccessibleName = "安装位置"; location.TabIndex = 0;
        string existing = preview ? null : Product.InstalledPath;
        location.Text = preview ? "D:\\Apps\\" + Path.GetFileNameWithoutExtension(Product.Exe) : existing ?? Product.DefaultPath;
        location.Enter += delegate { path.Invalidate(); }; location.Leave += delegate { path.Invalidate(); };
        path.Controls.Add(location); Controls.Add(path);
        browse.Text = "更改…"; browse.Location = new Point(632,192); browse.Size = new Size(92,44); browse.TabIndex = 1;
        browse.Click += delegate {
            using (var picker = new FolderBrowserDialog()) {
                picker.Description = "选择存放桌宠的位置。将自动建立 " + Path.GetFileNameWithoutExtension(Product.Exe) + " 专用文件夹。";
                picker.ShowNewFolderButton = true;
                try { string current = Product.NormalizeInstallPath(location.Text); picker.SelectedPath = Directory.Exists(current) ? current : Path.GetDirectoryName(current); } catch { }
                if (picker.ShowDialog(this) == DialogResult.OK) {
                    string selected = picker.SelectedPath;
                    location.Text = File.Exists(Path.Combine(selected,Product.Marker)) || String.Equals(Path.GetFileName(selected),Path.GetFileNameWithoutExtension(Product.Exe),StringComparison.OrdinalIgnoreCase)
                        ? selected : Path.Combine(selected,Path.GetFileNameWithoutExtension(Product.Exe));
                }
            }
        };
        Controls.Add(browse);
        Controls.Add(Caption("可直接编辑路径，也可选择其他磁盘。",276,246,448,22,9,false,muted));
        desktop.Text = "创建桌面快捷方式"; desktop.Checked = true; desktop.Location = new Point(276,287); desktop.Size = new Size(222,28); desktop.TabIndex = 2;
        launch.Text = "安装后启动"; launch.Location = new Point(514,287); launch.Size = new Size(200,28); launch.TabIndex = 3;
        status.Text = existing == null ? "个人设置单独保存，升级时会保留。" : "已找到安装目录，将在原位置升级。";
        status.ForeColor = muted; status.Location = new Point(276,329); status.Size = new Size(448,63); status.Font = new Font("Microsoft YaHei UI",9);
        progress.Location = new Point(276,397); progress.Size = new Size(448,4); progress.Visible = false;
        Controls.Add(Caption("Windows x64 · 仅当前用户",276,431,240,24,9,false,muted));
        cancel.Text = "取消"; cancel.Location = new Point(508,418); cancel.Size = new Size(80,42); cancel.TabIndex = 5; cancel.Click += delegate { Close(); };
        install.Text = existing == null ? "开始安装" : "升级安装"; install.Location = new Point(600,418); install.Size = new Size(124,42); install.TabIndex = 4;
        install.Click += delegate { StartInstall(); };
        Controls.AddRange(new Control[] {desktop,launch,status,progress,cancel,install});
        AcceptButton = install; CancelButton = cancel;
        FormClosing += delegate(object sender, FormClosingEventArgs e) { if (busy) e.Cancel = true; };
        ResumeLayout(false);
    }
    void SetBusy(bool value) {
        busy = value; location.Enabled = browse.Enabled = desktop.Enabled = launch.Enabled = cancel.Enabled = install.Enabled = !value;
    }
    void StartInstall() {
        if (completed) { Close(); return; }
        string root;
        try { root = Product.NormalizeInstallPath(location.Text); Product.ValidateUpgradeLocation(root,Product.InstalledPath); }
        catch (Exception e) { status.ForeColor = Color.FromArgb(157,66,58); status.Text = e.Message; location.Focus(); return; }
        location.Text = root; bool makeShortcut = desktop.Checked, startAfter = launch.Checked;
        SetBusy(true); progress.Value = 0; progress.Visible = true; status.ForeColor = muted; status.Text = "正在安放你的桌面伙伴…";
        var worker = new Thread(delegate() {
            Exception failure = null;
            try {
                int last = -1;
                Package.Install(root,true,makeShortcut,delegate(int percent) {
                    if (percent != last) { last = percent; BeginInvoke(new Action(delegate { progress.Value = percent; })); }
                });
            } catch (Exception e) { failure = e; }
            BeginInvoke(new Action(delegate {
                SetBusy(false);
                if (failure != null) {
                    progress.Visible = false; status.ForeColor = Color.FromArgb(157,66,58);
                    status.Text = failure is UnauthorizedAccessException ? "这个位置没有写入权限，请选择你有权限的文件夹，或使用默认位置。" : failure.Message;
                    return;
                }
                completed = true; progress.Value = 100; status.ForeColor = Color.FromArgb(54,107,86);
                status.Text = "安装完成。你的桌面伙伴已经准备好了。"; install.Text = "完成"; cancel.Visible = false;
                location.Enabled = browse.Enabled = desktop.Enabled = launch.Enabled = false;
                if (startAfter) try { Process.Start(new ProcessStartInfo(Path.Combine(root,Product.Exe)) { WorkingDirectory = root }); }
                catch { status.Text = "安装完成。自动启动未成功，可从开始菜单打开。"; }
            }));
        });
        worker.SetApartmentState(ApartmentState.STA); worker.IsBackground = true; worker.Start();
    }
    protected override void Dispose(bool disposing) { if (disposing && avatar.Image != null) avatar.Image.Dispose(); base.Dispose(disposing); }
}
#endif

static class Entry {
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    [STAThread]
    static int Main(string[] args) {
        SetProcessDPIAware();
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        try {
#if UNINSTALLER
            if (args.Length == 2 && args[0] == "--remove") {
                Thread.Sleep(800); Product.Uninstall(args[1], true);
                MessageBox.Show("小薛同学桌宠已卸载。个人设置仍保存在 %LOCALAPPDATA%\\XiaoxuePet。", Product.Name); return 0;
            }
            string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            Product.EnsureClosed(root); Product.Owned(root);
            if (MessageBox.Show("卸载小薛同学桌宠？个人设置会保留。", Product.Name, MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes) {
                string helper = Path.Combine(Path.GetTempPath(), "XiaoxueUninstall-" + Guid.NewGuid().ToString("N") + ".exe");
                File.Copy(Assembly.GetExecutingAssembly().Location, helper);
                Process.Start(new ProcessStartInfo(helper, "--remove \"" + root + "\"") { UseShellExecute = false });
            }
#else
            if (args.Length == 2 && args[0] == "--capture") {
                using (var window = new SetupWindow(true)) {
                    window.ShowInTaskbar = false; window.Opacity = 0;
                    window.Show(); Application.DoEvents();
                    using (var bitmap = new Bitmap(window.Width, window.Height)) {
                        window.DrawToBitmap(bitmap, new Rectangle(Point.Empty, window.Size));
                        bitmap.Save(args[1], System.Drawing.Imaging.ImageFormat.Png);
                    }
                }
                return 0;
            }
            // Deterministic test extraction: no registry or shortcut changes.
            if (args.Length == 2 && args[0] == "--validate-path-test") { Product.NormalizeInstallPath(args[1]); return 0; }
            if (args.Length == 3 && args[0] == "--upgrade-path-test") { Product.ValidateUpgradeLocation(args[1],args[2]); return 0; }
            if (args.Length == 2 && args[0] == "--extract-test") { Package.Install(args[1], false, false); return 0; }
            if (args.Length == 2 && args[0] == "--uninstall-test") { Product.Uninstall(args[1], false); return 0; }
            Application.Run(new SetupWindow());
#endif
            return 0;
        } catch (Exception e) {
            if (args.Length > 0 && args[0].EndsWith("-test")) { try { File.WriteAllText(Path.Combine(Path.GetTempPath(), Product.Exe + "-setup-test-" + Process.GetCurrentProcess().Id + ".txt"), e.ToString()); } catch { } return 1; }
            MessageBox.Show(e.Message, Product.Name, MessageBoxButtons.OK, MessageBoxIcon.Error); return 1;
        }
    }
}
