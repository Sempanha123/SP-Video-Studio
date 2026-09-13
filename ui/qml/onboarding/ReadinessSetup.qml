import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Onboarding 1.0
import "../theme"
import "../components"

SetupStep {
    id: root
    title: "System readiness"
    description: "A quick best-effort check. Missing GPU or AI models do not make the editor unusable."
    Component.onCompleted: if (!Onboarding.checkingReadiness && Object.keys(Onboarding.readiness).length === 0) Onboarding.refreshReadiness()
    RowLayout { Layout.fillWidth: true
        StatusBadge { text: Onboarding.checkingReadiness ? "Checking" : (Onboarding.readiness.overallDisplay || "Not checked"); status: Onboarding.checkingReadiness ? "checking" : (Onboarding.readiness.overallStatus || "unknown") }
        Item { Layout.fillWidth: true }
        SecondaryButton { text: "Recheck"; enabled: !Onboarding.checkingReadiness; onClicked: Onboarding.refreshReadiness() }
    }
    GridLayout {
        Layout.fillWidth: true; columns: width < 650 ? 1 : 2; columnSpacing: Theme.spacing.md; rowSpacing: Theme.spacing.md
        ReadinessItem { Layout.fillWidth: true; name: "FFmpeg"; statusText: Onboarding.readiness.ffmpegAvailable ? "Ready" : "Needs Setup"; status: Onboarding.readiness.ffmpegAvailable ? "ready" : "setup-required"; detail: Onboarding.readiness.renderingMessage || "Checking rendering tools…" }
        ReadinessItem { Layout.fillWidth: true; name: "Storage"; statusText: (Onboarding.readiness.disks && Onboarding.readiness.disks.length) ? "Checked" : "Optional"; status: "ready"; detail: (Onboarding.readiness.disks && Onboarding.readiness.disks.length) ? String(Onboarding.readiness.disks[0].detail || "Storage checked") : "Storage details unavailable" }
        ReadinessItem { Layout.fillWidth: true; name: "CPU"; statusText: Onboarding.readiness.cpuName ? "Ready" : "Optional"; status: "ready"; detail: (Onboarding.readiness.cpuName || "CPU mode") + " · " + (Onboarding.readiness.cpuLogicalCores || "?") + " logical cores" }
        ReadinessItem { Layout.fillWidth: true; name: "GPU"; statusText: Onboarding.readiness.gpuStatus === "ready" ? "Acceleration Available" : "CPU Mode Available"; status: Onboarding.readiness.gpuStatus === "ready" ? "ready" : "warning"; detail: Onboarding.readiness.cpuModeMessage || "CPU mode remains available." }
        ReadinessItem { Layout.fillWidth: true; name: "Voice AI"; statusText: Onboarding.readiness.voxcpmStatus === "installed" ? "Installed" : "Optional"; status: Onboarding.readiness.voxcpmStatus === "installed" ? "ready" : "warning"; detail: "VoxCPM2 can be installed later from Models." }
        ReadinessItem { Layout.fillWidth: true; name: "Speech Recognition"; statusText: Onboarding.readiness.whisperStatus === "installed" ? "Installed" : "Optional"; status: Onboarding.readiness.whisperStatus === "installed" ? "ready" : "warning"; detail: "faster-whisper is optional; transcripts can still be edited manually." }
    }
    RowLayout { Layout.fillWidth: true
        SecondaryButton { text: "Choose FFmpeg"; visible: !Onboarding.readiness.ffmpegAvailable; onClicked: Onboarding.openSettings("Performance") }
        SecondaryButton { text: "Open Setup Help"; visible: !Onboarding.readiness.ffmpegAvailable; onClicked: Onboarding.openSettings("Performance") }
        Item { Layout.fillWidth: true }
    }
}
