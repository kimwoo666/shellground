// Built by Windows PowerShell's Add-Type against the inbox .NET Framework.
// The installer pins both HTTPS URLs and SHA-256, and never executes a chunk.
using System;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using System.IO.Compression;
using System.Runtime.InteropServices;

public sealed class ReleasePart {
    public string Name;
    public string Hash;
    public long Bytes;
}

public sealed class ShellgroundSetup {
    const string Owner = "shellground-setup-v1";
    const string BaseUrl = "https://github.com/kimwoo666/shellground/releases/download/v4.7.4-preview/";
    const string Version = "4.7.6";
    const string AppBaseUrl = "https://github.com/kimwoo666/shellground/releases/download/v" + Version + "/";
    readonly CancellationTokenSource cancellation = new CancellationTokenSource();
    public volatile string Stage = "설치 준비 중";
    public volatile string Error = null;
    public volatile bool Finished = false;
    public volatile bool Succeeded = false;
    public long Current;
    public long Total;
    public string Application;
    public string EmbeddedApplicationPath;
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CreateHardLink(string link, string existing, IntPtr reserved);
    public void Cancel() { cancellation.Cancel(); }
    static string HashFile(string path) {
        using (var input = File.OpenRead(path))
        using (var hash = SHA256.Create()) { return Hex(hash.ComputeHash(input)); }
    }
    static string Hex(byte[] bytes) { return BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant(); }
    static void SafePath(string path) {
        if ((File.Exists(path) || Directory.Exists(path)) &&
            (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
            throw new IOException("설치 경로는 링크일 수 없습니다: " + path);
    }
    void StopCheck() { cancellation.Token.ThrowIfCancellationRequested(); }
    void Receive(HttpClient client, ReleasePart part, string target, long offset, long total, bool application = false) {
        StopCheck(); SafePath(target);
        Stage = "실습 자료 내려받는 중";
        Interlocked.Exchange(ref Current, offset); Interlocked.Exchange(ref Total, total);
        using (var output = new FileStream(target, FileMode.OpenOrCreate, FileAccess.Write, FileShare.None)) {
            output.SetLength(offset); output.Position = offset;
            try {
                using (var response = client.GetAsync((application ? AppBaseUrl : BaseUrl) + part.Name,
                    HttpCompletionOption.ResponseHeadersRead, cancellation.Token).GetAwaiter().GetResult()) {
                    response.EnsureSuccessStatusCode();
                    using (var input = response.Content.ReadAsStreamAsync().GetAwaiter().GetResult())
                    using (var hash = SHA256.Create()) {
                        var buffer = new byte[256 * 1024]; long count = 0; int read;
                        while (true) {
                            StopCheck();
                            var task = input.ReadAsync(buffer, 0, buffer.Length, cancellation.Token);
                            if (!task.Wait(30000, cancellation.Token)) throw new IOException("다운로드 응답이 지연됐습니다. 다시 시도하세요.");
                            read = task.GetAwaiter().GetResult();
                            if (read == 0) break;
                            count += read;
                            if (count > part.Bytes) throw new IOException("다운로드 크기 불일치");
                            output.Write(buffer, 0, read);
                            hash.TransformBlock(buffer, 0, read, buffer, 0);
                            Interlocked.Exchange(ref Current, offset + count);
                        }
                        hash.TransformFinalBlock(new byte[0], 0, 0);
                        if (count != part.Bytes || Hex(hash.Hash) != part.Hash)
                            throw new IOException("파일 검증 실패. 다시 시도하면 해당 자료만 다시 받습니다.");
                        output.Flush(true);
                    }
                }
            } catch { output.SetLength(offset); throw; }
        }
    }
    void Disk(HttpClient client, string path, ReleasePart[] parts, string hash, long bytes) {
        string partial = path + ".partial", checkpoint = path + ".checkpoint";
        SafePath(path); SafePath(partial); SafePath(checkpoint);
        if (File.Exists(path)) {
            Stage = "기존 실습 자료 확인 중";
            if (new FileInfo(path).Length == bytes && HashFile(path) == hash) return;
            throw new IOException("기존 실습 자료가 변경됐습니다. 다른 빈 폴더에 설치하세요.");
        }
        int done = 0;
        if (File.Exists(checkpoint) && File.Exists(partial)) {
            var fields = File.ReadAllText(checkpoint).Split(':');
            if (fields.Length == 2 && fields[0] == hash) Int32.TryParse(fields[1], out done);
        }
        if (done < 0 || done > parts.Length) done = 0;
        long offset = 0; for (int i = 0; i < done; ++i) offset += parts[i].Bytes;
        if (!File.Exists(partial) || new FileInfo(partial).Length < offset) { done = 0; offset = 0; }
        var drive = new DriveInfo(Path.GetPathRoot(path));
        if (drive.AvailableFreeSpace < bytes - offset + 256L * 1024 * 1024)
            throw new IOException("설치에는 약 9GB의 여유 공간이 필요합니다.");
        for (int i = done; i < parts.Length; ++i) {
            Receive(client, parts[i], partial, offset, bytes);
            offset += parts[i].Bytes;
            // A torn checkpoint can only cause a part to be downloaded again;
            // the complete disk SHA is always verified before it is activated.
            File.WriteAllText(checkpoint, hash + ":" + (i + 1));
        }
        StopCheck(); Stage = "다운로드 완료 · 전체 파일 확인 중";
        if (new FileInfo(partial).Length != bytes || HashFile(partial) != hash) {
            File.WriteAllText(checkpoint, hash + ":0");
            throw new IOException("전체 실습 파일 검증에 실패했습니다. 다시 시도하세요.");
        }
        File.Move(partial, path); File.Delete(checkpoint);
    }
    void ReuseDisk(string root, string target, string hash, long bytes) {
        if (File.Exists(target)) return;
        // Only known, installed releases under this installer-owned root.
        foreach (string version in new string[] { "4.7.5", "4.7.4" }) {
            string old = Path.Combine(root, "app-" + version);
            string receipt = Path.Combine(old, "installed.sha256");
            string disk = Path.Combine(old, "runtime", "windows-x86_64", "base.qcow2");
            SafePath(old); SafePath(receipt); SafePath(disk);
            if (!File.Exists(receipt) || !File.Exists(disk)) continue;
            if (!File.ReadAllText(receipt).StartsWith(hash + ":", StringComparison.Ordinal)) continue;
            Stage = "기존 실습 자료 확인 · 재다운로드 방지";
            if (new FileInfo(disk).Length != bytes || HashFile(disk) != hash) continue;
            StopCheck();
            // Practice always uses separate overlays; this base stays immutable.
            if (CreateHardLink(target, disk, IntPtr.Zero)) return;
        }
    }
    void Extract(string archive, string destination) {
        Stage = "프로그램 설치 중";
        string prefix = Path.GetFullPath(destination) + Path.DirectorySeparatorChar;
        using (var zip = ZipFile.OpenRead(archive)) {
            foreach (var entry in zip.Entries) {
                StopCheck();
                const string top = "Shellground-Windows/";
                if (!entry.FullName.StartsWith(top, StringComparison.Ordinal)) throw new IOException("잘못된 압축 경로");
                string relative = entry.FullName.Substring(top.Length);
                if (relative.Length == 0) continue;
                if (relative.Contains(":")) throw new IOException("잘못된 압축 파일명");
                string path = Path.GetFullPath(Path.Combine(destination, relative));
                if (!path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) throw new IOException("압축 경로 이탈");
                SafePath(path);
                if (entry.FullName.EndsWith("/")) { Directory.CreateDirectory(path); continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                entry.ExtractToFile(path, true);
            }
        }
    }
    public void Start(string root, ReleasePart archive, ReleasePart[] parts, string diskHash, long diskBytes) {
        Task.Run(delegate {
            try {
                SafePath(root); Directory.CreateDirectory(root);
                string owner = Path.Combine(root, ".shellground-installer"); SafePath(owner);
                if (File.Exists(owner)) {
                    if (File.ReadAllText(owner) != Owner) throw new IOException("다른 프로그램의 설치 폴더입니다.");
                } else {
                    if (Directory.GetFileSystemEntries(root).Length != 0) throw new IOException("비어 있는 폴더를 사용하세요.");
                    File.WriteAllText(owner, Owner);
                }
                string lockPath = Path.Combine(root, ".setup.lock"); SafePath(lockPath);
                using (var fileLock = new FileStream(lockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None)) {
                    Application = Path.Combine(root, "app-" + Version);
                    string receipt = Path.Combine(Application, "installed.sha256");
                    SafePath(Application); SafePath(receipt);
                    string identity = diskHash + ":" + archive.Hash;
                    if (File.Exists(receipt) && File.ReadAllText(receipt) == identity &&
                        File.Exists(Path.Combine(Application, "Shellground.exe"))) { Succeeded = true; return; }
                    if (Directory.Exists(Application)) throw new IOException("같은 버전의 기존 폴더가 있습니다. 빈 폴더를 사용하세요.");
                    string incoming = Path.Combine(root, ".incoming-" + Version); SafePath(incoming); Directory.CreateDirectory(incoming);
                    string ready = Path.Combine(incoming, ".app-ready"); SafePath(ready);
                    ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
                    using (var client = new HttpClient()) {
                        client.Timeout = TimeSpan.FromSeconds(30);
                        client.DefaultRequestHeaders.UserAgent.ParseAdd("Shellground-Setup/" + Version);
                        if (!File.Exists(ready)) {
                            string payload = Path.Combine(root, "application.zip.partial"); SafePath(payload);
                            bool embedded = !String.IsNullOrEmpty(EmbeddedApplicationPath) && File.Exists(EmbeddedApplicationPath);
                            if (embedded) {
                                payload = EmbeddedApplicationPath; SafePath(payload);
                                if (new FileInfo(payload).Length != archive.Bytes || HashFile(payload) != archive.Hash)
                                    throw new IOException("내장 프로그램 파일 검증 실패");
                            } else if (!File.Exists(payload) || HashFile(payload) != archive.Hash) Receive(client, archive, payload, 0, archive.Bytes, true);
                            Extract(payload, incoming); File.WriteAllText(ready, archive.Hash);
                            if (!embedded) File.Delete(payload);
                        } else if (File.ReadAllText(ready) != archive.Hash) throw new IOException("설치 자료 버전 불일치");
                        string targetDisk = Path.Combine(incoming, "runtime", "windows-x86_64", "base.qcow2");
                        ReuseDisk(root, targetDisk, diskHash, diskBytes);
                        Disk(client, targetDisk, parts, diskHash, diskBytes);
                    }
                    StopCheck(); File.WriteAllText(Path.Combine(incoming, "installed.sha256"), identity);
                    Directory.Move(incoming, Application); Succeeded = true;
                }
            } catch (OperationCanceledException) { Error = "취소했습니다. 다음 설치에서 이어 받습니다."; }
              catch (Exception error) { Error = error.GetBaseException().Message; }
            finally { Finished = true; }
        });
    }
}
