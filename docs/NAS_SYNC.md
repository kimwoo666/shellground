# NAS learning-progress sync

[한국어 안내](NAS_SYNC.ko.md)

Use **Progress sync / 진도 동기화 → NAS connection settings** and select the same private NAS folder on each computer. Only the first device should create a new profile in an empty, dedicated folder. Windows can use a mapped share or UNC path; Linux can use a mounted folder or an existing authenticated rclone connection. Desktop uses the operating system's existing credentials.

On Android, open **NAS progress sync** in the study menu and enter the NAS server, share, relative progress folder, account and password. Create the initial profile on a desktop first. For the illustrative Windows path `\\nas.local\study\Shellground\progress-v1`, enter server `nas.local`, share `study`, folder `Shellground/progress-v1`. Android connects directly using signed SMB 2/3 without a PC. Use your LAN or private VPN; do not expose SMB to the Internet. Connection details are encrypted with an Android Keystore AES-GCM key, stored in app-private no-backup storage and never included in progress exports. Disconnecting removes local login settings, not earned progress.

The app downloads progress before opening study pages. During study it saves in the background; **F9** requests an immediate save. Before switching computers, wait for **NAS 저장 완료**. Remote changes are applied at the next launch, not in the middle of an exercise. Offline work stays local and retries later. Closing has a bounded final-sync wait; unsent changes require reconnecting that device later.

Synced: completed units, substeps, practice/quiz records and memory notes. Excluded: VM disks, practice files, typed source, terminal history, credentials and display settings. Completion sets are merged, not overwritten. Concurrent note edits are retained as separate notes. Sync does not propagate resets of earned completion. Changed local files are backed up before remote progress is applied.

Each device owns one bounded JSON snapshot. The shared profile marker prevents accidental profile mixing. Missing mounts, malformed documents and unsupported schemas leave local progress intact. Keep NAS access restricted to the learning profile's owner.

Every device needs a version containing this feature. Android migrates existing completion and learning positions into the shared format without deleting unknown desktop records. Python/Conda/Jupyter practice passes, Linux/Docker/ROS 2 unit and review completion, explanation positions and concept quizzes are supported. Desktop-only memory notes are preserved, not given a new Android editor. On Android, incoming progress is applied at process startup: close the app fully and reopen it. **Save to NAS now** requests an upload before switching devices. If Android kills the process before upload finishes, unsent progress remains local for the next launch. Course content is updated with the app, not through the personal progress folder.

Personal NAS addresses, profile IDs, credentials and learning records are excluded from published sources and installer defaults. Packaging an update does not imply native Windows hardware validation; consult its verification receipt for what was actually tested.
