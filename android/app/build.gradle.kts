plugins {
    id("com.android.application")
    id("com.chaquo.python")
}
val linuxRuntime = providers.gradleProperty("linuxRuntime").orNull == "true"
val bundleLinuxPack = providers.gradleProperty("bundleLinuxPack").orNull == "true"
val reuseReleaseRuntime = providers.gradleProperty("reuseReleaseRuntime").orNull
val reuseJavaPayload = providers.gradleProperty("reuseJavaPayload").orNull
require(reuseJavaPayload == null || (linuxRuntime && bundleLinuxPack && reuseReleaseRuntime == null)) {
    "reuseJavaPayload requires linuxRuntime=true, bundleLinuxPack=true, and no reuseReleaseRuntime"
}
android {
    namespace = "org.shellground.learn"
    compileSdk = 35
    defaultConfig {
        applicationId = "org.shellground.learn"
        minSdk = 24
        targetSdk = 35
        versionCode = 477
        versionName = "4.7.7"
        buildConfigField("boolean", "LINUX_RUNTIME", linuxRuntime.toString())
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
    }
    buildFeatures { buildConfig = true }
    packaging.jniLibs { useLegacyPackaging = true; keepDebugSymbols += "**/libshellground_qemu.so" }
    if (linuxRuntime) sourceSets.getByName("main").jniLibs.srcDir(layout.buildDirectory.dir("generated/realJniLibs"))
    if (bundleLinuxPack) {
        require(linuxRuntime) { "bundleLinuxPack requires linuxRuntime=true" }
        sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/realAssets"))
        androidResources.noCompress += "sgpart"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    signingConfigs.getByName("debug") {
        storeFile = file(System.getenv("SHELLGROUND_ANDROID_KEYSTORE") ?: "../../desktop/.android-tools/debug.keystore")
        storePassword = "android"
        keyAlias = "androiddebugkey"
        keyPassword = "android"
    }
    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/assets"))
    sourceSets.getByName("main").java.srcDir("../runtime/src/main/java")
    if (reuseJavaPayload != null) {
        sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/javaPayload/assets"))
        sourceSets.getByName("main").jniLibs.srcDir(layout.buildDirectory.dir("generated/javaPayload/jniLibs"))
    }
}
val stageLinuxRuntime by tasks.registering(Exec::class) {
    onlyIf { reuseReleaseRuntime == null }
    commandLine("python3", "../runtime/stage_candidates.py", "--destination",
        layout.buildDirectory.dir("generated/realJniLibs").get().asFile.absolutePath)
}
val stageLinuxPack by tasks.registering(Exec::class) {
    onlyIf { reuseReleaseRuntime == null }
    // Java/UI-only edits must not hash and rewrite the entire 1.7GB guest on
    // every build. Gradle invalidates this local up-to-date check when either
    // a source, the verifier, or any generated output changes. The stage tool
    // still validates every source checksum whenever the task actually runs.
    val pack = file("../.native-runtime/android-pack-4.7.4")
    inputs.files(listOf("base.qcow2", "kernel", "initrd", "manifest.json").map { pack.resolve(it) })
    inputs.file("../runtime/stage_app_pack.py")
    outputs.dir(layout.buildDirectory.dir("generated/realAssets/training-pack"))
    commandLine("python3", "../runtime/stage_app_pack.py", "--source", pack.absolutePath, "--destination",
        layout.buildDirectory.dir("generated/realAssets/training-pack").get().asFile.absolutePath)
}
dependencies {
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.16.1")
    implementation("com.hierynomus:smbj:0.14.0")
    runtimeOnly("org.slf4j:slf4j-nop:2.0.16")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
val stagePython by tasks.registering(Sync::class) {
    from("../../desktop/python_teaching") { into("python_teaching"); include("*.py", "quiz_bank.json", "concept_cards.json"); exclude("engine.py") }
    from("../../desktop/assets/NotoSansCJK-Regular.ttc") { into("assets") }
    from("src/main/python")
    from("../../desktop/nas_sync.py")
    // Same existing VT parser as desktop; no shell simulation or host exec.
    from("../../desktop/.runtime/pyte") { into("pyte"); include("**/*.py") }
    from("../../desktop/.runtime/wcwidth") { into("wcwidth"); include("**/*.py") }
    from("../../desktop/.runtime/pyte-0.8.2.dist-info/LICENSE") { into("licenses/pyte") }
    from("../../desktop/.runtime/wcwidth-0.8.3.dist-info/licenses/LICENSE") { into("licenses/wcwidth") }
    into(layout.buildDirectory.dir("generated/python"))
}
val exportRealCourse by tasks.registering(Exec::class) {
    commandLine(System.getenv("SHELLGROUND_BUILD_PYTHON") ?: "python3.13", "../../desktop/export_real_course.py",
        layout.buildDirectory.file("generated/assets/real-course.json").get().asFile.absolutePath)
    inputs.files(fileTree("../../desktop") { include("*.py") })
    outputs.file(layout.buildDirectory.file("generated/assets/real-course.json"))
}
val exportCourse by tasks.registering(Exec::class) {
    commandLine(System.getenv("SHELLGROUND_BUILD_PYTHON") ?: "python3.13", "../../desktop/export_python_course.py",
        layout.buildDirectory.file("generated/assets/python-course.json").get().asFile.absolutePath)
    inputs.files(fileTree("../../desktop/python_teaching") { include("*.py", "quiz_bank.json", "concept_cards.json") })
    outputs.file(layout.buildDirectory.file("generated/assets/python-course.json"))
}
val exportPortCourses by tasks.registering(Exec::class) {
    val arguments=mutableListOf(System.getenv("SHELLGROUND_BUILD_PYTHON") ?: "python3.13", "../runtime/export_port_assets.py", "--destination",
        layout.buildDirectory.dir("generated/portAssets").get().asFile.absolutePath)
    if(reuseReleaseRuntime != null)arguments.add("--reuse-wheel-identity")
    commandLine(arguments)
    inputs.files(fileTree("../../desktop/conda_teaching") { include("*.py", "*course_spec.json") })
    inputs.files(fileTree("../../desktop/notebook_teaching") { include("*.py") })
    inputs.files(fileTree("../../desktop/guest") { include("*.py", "bashrc") })
    inputs.files("../runtime/export_port_assets.py", "../../desktop/lab/lab.py")
    outputs.dir(layout.buildDirectory.dir("generated/portAssets"))
}
val restoreReleaseRuntime by tasks.registering(Exec::class) {
    onlyIf { reuseReleaseRuntime != null }
    commandLine("python3", "../runtime/reuse_release_runtime.py", reuseReleaseRuntime?.let { rootProject.file(it).absolutePath } ?: "")
    if(reuseReleaseRuntime != null)inputs.file(rootProject.file(reuseReleaseRuntime))
    inputs.file("../runtime/reuse_release_runtime.py")
    outputs.dirs(layout.buildDirectory.dir("generated/realJniLibs"),layout.buildDirectory.dir("generated/realAssets"))
}
tasks.named("exportPortCourses") { if(reuseReleaseRuntime != null)dependsOn(restoreReleaseRuntime) }
android.sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/portAssets"))
chaquopy {
    defaultConfig {
        version = "3.13"
        buildPython(System.getenv("SHELLGROUND_BUILD_PYTHON") ?: "python3.13")
        pip {
            options("--extra-index-url", "https://chaquo.com/pypi-upstream/")
            options("--find-links", rootProject.file("../desktop/.android-tools/wheels").absolutePath)
            install("chaquopy-freetype==2.14.3")
            install("numpy==1.26.2")
            install("matplotlib==3.8.4")
            install("pandas==2.1.3")
            install("scipy==1.16.1")
            install("seaborn==0.13.2")
            install("scikit-learn==1.7.1")
        }
    }
    sourceSets.getByName("main") { setSrcDirs(listOf(layout.buildDirectory.dir("generated/python"))) }
}
tasks.named("preBuild") { dependsOn(stagePython, exportCourse, exportRealCourse, exportPortCourses) }
tasks.named("preBuild") {
    if (linuxRuntime) dependsOn(stageLinuxRuntime)
    if (bundleLinuxPack) dependsOn(stageLinuxPack)
}
tasks.configureEach {
    if (name.contains("PythonSources")) dependsOn(stagePython)
    if (reuseJavaPayload != null && (name.contains("Python") ||
        name in setOf("stagePython", "stageLinuxRuntime", "stageLinuxPack", "exportCourse", "exportRealCourse", "exportPortCourses"))) {
        enabled = false
    }
}

val restoreJavaPayload by tasks.registering(Exec::class) {
    onlyIf { reuseJavaPayload != null }
    commandLine(System.getenv("SHELLGROUND_BUILD_PYTHON") ?: "python3.13", "../runtime/reuse_java_payload.py",
        reuseJavaPayload?.let { rootProject.file(it).absolutePath } ?: "")
    // Always recheck the source guard; changes in course inputs must not silently
    // reuse stale Python just because the APK itself is unchanged.
}
tasks.named("preBuild") { if (reuseJavaPayload != null) dependsOn(restoreJavaPayload) }
