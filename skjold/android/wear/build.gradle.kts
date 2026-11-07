plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Samme signeringsnøkkel og samme applicationId som telefonappen – påkrevd for Wearable Data Layer.
val ksPath: String? = System.getenv("SKJOLD_KEYSTORE")
val hasKs = ksPath != null && file(ksPath).exists()

android {
    namespace = "no.kristo.skjold.wear"
    compileSdk = 35

    defaultConfig {
        applicationId = "no.kristo.skjold.app"
        minSdk = 30
        targetSdk = 34
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
        release {
            isMinifyEnabled = false
            signingConfig = if (hasKs) signingConfigs.getByName("skjold") else signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    lint { abortOnError = false }
    buildFeatures { compose = true }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.wear.compose:compose-material:1.4.0")
    implementation("androidx.wear.compose:compose-foundation:1.4.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.9.0")
    implementation("com.google.android.gms:play-services-wearable:18.2.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("io.coil-kt:coil-compose:2.7.0")
}
