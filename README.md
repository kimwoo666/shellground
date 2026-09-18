<div align="center">

# Shellground

### Learn by doing. Check the result. Keep improving.

A native practice app for **Linux · Docker · ROS 2 · Python · Conda · Jupyter**.

**English** · [한국어](README.ko.md)

[Downloads](https://github.com/kimwoo666/shellground/releases/tag/v4.7.4-preview) · [Getting started](docs/GETTING_STARTED.md) · [Platform & verification notes](docs/PLATFORMS.md)

</div>

![Shellground's native Linux learning screen](docs/screenshots/linux-learning.png)

Shellground turns a command or a library into a sequence of short, hands-on lessons. Read a concept, try it, solve a different task, then revisit what you learned in mixed practice. It checks the resulting files, processes, variables and plots—not just whether you typed a sample answer.

This is an installed application, **not a website or a WebView**. Lesson content is currently in Korean; this introduction and the getting-started guide are available in English and Korean.

## A practical learning loop

1. **Learn one concept at a time.** Small explanation steps with room to try the command or code.
2. **Work through an example.** Understand the starting directory, inputs and expected result.
3. **Solve application tasks.** Repair a broken state, preserve an original, or combine earlier skills.
4. **Get specific feedback.** Failed checks do not force a reset; keep working in the same session.
5. **Review and mix.** Review blocks and learned-range random practice help you retain older material.

Completed lessons and your position within a lesson are saved automatically. Typed code, terminal sessions and temporary practice files are not a permanent workspace.

## One app, several learning tracks

| Track | Included learning material |
| --- | --- |
| Linux | 90 units + 18 reviews: navigation, files, quoting, relative paths, editors, streams, permissions, accounts, packages and processes |
| Docker | 25 units + 5 reviews: images, containers, registries, files, volumes, networks, builds, lifecycle and resource observation |
| ROS 2 | 23 units + 4 reviews: workspaces, nodes, topics, services, parameters, launch, bags and terminal controls |
| Python & data | 95 units/reviews, 285 tasks: Python, NumPy, Matplotlib, pandas, SciPy, Seaborn and scikit-learn |
| Conda & pip | 20 units/reviews, 60 tasks, plus an optional installation exercise |
| Jupyter | 6 units/reviews, 18 tasks: real kernel selection, cell order, state, environment and notebook saving |

Counts describe the included curriculum, not a claim that every upstream command option or every device feature is covered. See [scope and limitations](docs/PLATFORMS.md).

## Real results, readable feedback

![Python code and an actual Matplotlib plot](docs/screenshots/python-plot.png)

**Run code and inspect the result.** Python uses bundled CPython and scientific libraries. Plot tasks inspect the actual figure and its data, not a screenshot match.

![Per-goal feedback after running the example](docs/screenshots/python-grading.png)

**Fix only what is missing.** The question and grading panels share their space. You can return to the task without restarting the practice environment.

<p align="center"><img src="docs/screenshots/android-notebook.png" width="320" alt="Native Android Jupyter lesson screen"></p>

**Practice on Android without a PC.** Native mobile tabs give the explanation, terminal, notebook and feedback their own usable space. Linux-based practice runs inside the app's bundled ARM64 Linux environment.

These are captures of the application, not concept mockups. Desktop captures are from Linux; they are not evidence of native Windows execution.

## Download and run

Get the versioned files from [Releases](https://github.com/kimwoo666/shellground/releases/tag/v4.7.4-preview). Keep the complete desktop package together: the executable alone does not contain the Linux practice disk.

| Platform | Package | Verification boundary |
| --- | --- | --- |
| Linux x86-64 | Portable bundle | Built and exercised on the development Linux laptop |
| Windows x64 | Portable ZIP with `Shellground.exe` | Windows executable built using Wine; **not run on a native Windows PC** |
| Android | Standalone APK | Changed functionality checked on an Android emulator; **physical ARM phones not verified** |
| macOS | — | Not included in this release |

No separate Python, Docker, Conda, WSL, Termux or practice server is required for the bundled courses. Booting the included Linux environment takes time and uses more memory than the Python-only workspace. The packages are unsigned/development-signed; they are not store-certified releases.

Start with [the installation guide](docs/GETTING_STARTED.md). Desktop shortcuts include **Shift+Enter** for Python execution, **F1** for hints, **F5** for grading and **F6** for the next step. Android also provides touch controls.

## Safety, progress and project layout

- Linux-based commands run in an app-owned disposable guest, not your personal Docker or WSL installation.
- Python's worker is a separate process, **not a hostile-code security sandbox**. Use trusted practice code.
- Closing the app stops its practice processes. Progress is separate from disposable practice files.
- The original lightweight simulator is retained on desktop, but real-environment courses are the primary path.

```text
desktop/              Native Qt app, shared curricula and graders
android/              Native Android app and guest integration
docs/                 Guides, platform notes and actual screenshots
```

Build products, VM images, SDKs, caches, signing keys, personal progress and lecture PDFs are not committed to Git. Download packages belong in Releases. Development notes: [desktop](desktop/README.md), [Android](android/README.md). Third-party software and corresponding-source information: [notices](THIRD_PARTY_NOTICES.md).
