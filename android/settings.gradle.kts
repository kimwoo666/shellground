pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }
rootProject.name = "ShellgroundAndroid"
include(":app")
// Isolated developer acceptance APK; never added to the learner application.
if (providers.gradleProperty("linuxProbe").orNull == "true") include(":runtime-probe")
