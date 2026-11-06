plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

// Fast signeringsnøkkel (GitHub-secret SKJOLD_KEYSTORE_B64 m.fl., se skjold/RELEASE.md) – samme mønster som Capacitor-appen.
val ksPath: String? = System.getenv("SKJOLD_KEYSTORE")
val hasKs = ksPath != null && file(ksPath).exists()

android {
    namespace = "no.kristo.skjold"
    compileSdk = 35

    defaultConfig {
        // Egen id, så den native appen kan ligge ved siden av Capacitor-appen (no.kristo.skjold).
        applicationId = "no.kristo.skjold.app"
        minSdk = 26
        targetSdk = 35
        // Settes fra release-taggen i CI (skjold-v1.2.3 -> 1.2.3 / 10203)
        versionCode = (project.findProperty("skjoldVersionCode") as String?)?.toIntOrNull() ?: 1
        versionName = (project.findProperty("skjoldVersionName") as String?) ?: "0.0.0"
    }

    signingConfigs {
        create("skjold") {
            if (hasKs) {
                storeFile = file(ksPath!!)
                storePassword = System.getenv("SKJOLD_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("SKJOLD_KEY_ALIAS") ?: "skjold"
                keyPassword = System.getenv("SKJOLD_KEY_PASSWORD") ?: System.getenv("SKJOLD_KEYSTORE_PASSWORD")
            }
        }
    }

    buildTypes {
        debug {
            if (hasKs) signingConfig = signingConfigs.getByName("skjold")
        }
        release {
            isMinifyEnabled = false
            // Uten fast nøkkel signeres release med debug-nøkkelen, så APK-en kan installeres direkte.
            signingConfig = if (hasKs) signingConfigs.getByName("skjold") else signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    // Media3 merker SimpleBasePlayer/MediaLibraryService som @UnstableApi; klassene bruker @OptIn, men lint skal ikke stoppe bygget
    lint { disable += "UnsafeOptInUsageError"; abortOnError = false }
    buildFeatures { compose = true }
    packaging { resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" } }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.animation:animation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("io.coil-kt:coil-svg:2.7.0")
    implementation("androidx.camera:camera-camera2:1.4.1")
    implementation("androidx.camera:camera-lifecycle:1.4.1")
    implementation("androidx.camera:camera-view:1.4.1")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")
    // Hjemskjerm-widgets (Glance), periodisk oppdatering og «Spiller nå»-medievarsling (MediaSession + MediaStyle)
    implementation("androidx.glance:glance-appwidget:1.1.1")
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    // Mediesystemet: Media3-økt/bibliotek (hurtigpanel, låseskjerm, Now Bar, gjenopptak) og medieruter (Medieutgang)
    implementation("androidx.media3:media3-session:1.5.1")
    implementation("androidx.media3:media3-common:1.5.1")
    implementation("androidx.mediarouter:mediarouter:1.7.0")
    implementation("com.google.guava:guava:33.3.1-android")
}
