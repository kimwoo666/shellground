plugins { id("com.android.application") }

android {
    namespace = "org.shellground.runtimeprobe"
    compileSdk = 35
    defaultConfig {
        applicationId = "org.shellground.runtimeprobe"
        minSdk = 28
        targetSdk = 35
        versionCode = 1
        versionName = "0.1-dev-probe"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    signingConfigs.getByName("debug") {
        storeFile = file("../../desktop/.android-tools/debug.keystore")
        storePassword = "android"
        keyAlias = "androiddebugkey"
        keyPassword = "android"
    }
    // PIE executable packaged as a native library, extracted by the installer.
    packaging.jniLibs {
        useLegacyPackaging = true
        keepDebugSymbols += "**/libshellground_qemu.so"
    }
    sourceSets.getByName("main").jniLibs.srcDir(layout.buildDirectory.dir("generated/jniLibs"))
    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/assets"))
    sourceSets.getByName("main").java.srcDir("../runtime/src/main/java")
}
dependencies {
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
val stageCandidates by tasks.registering(Exec::class) {
    commandLine("python3", "../runtime/stage_candidates.py", "--destination",
        layout.buildDirectory.dir("generated/jniLibs").get().asFile.absolutePath)
    // Always recheck the ELF and source/patch hashes, not just timestamps.
}
val stageBoot by tasks.registering(Exec::class) {
    commandLine("python3", "../runtime/stage_boot.py", "--destination",
        layout.buildDirectory.dir("generated/assets").get().asFile.absolutePath)
}
val stageGuestTest by tasks.registering(Exec::class) {
    commandLine("python3", "../runtime/stage_guest_test.py", "--destination",
        layout.buildDirectory.dir("generated/assets").get().asFile.absolutePath)
}
tasks.named("preBuild") { dependsOn(stageCandidates, stageBoot, stageGuestTest) }
