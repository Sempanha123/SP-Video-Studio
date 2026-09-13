import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Onboarding 1.0
import "../theme"
import "../components"

SetupStep {
    title: "You're ready"
    description: "Your setup is saved. Models can be installed later and advanced tools stay out of the way until you need them."
    GridLayout {
        Layout.fillWidth: true; columns: width < 650 ? 1 : 2; columnSpacing: Theme.spacing.md; rowSpacing: Theme.spacing.sm
        ReadinessItem { Layout.fillWidth: true; name: "Projects"; statusText: "Ready"; status: "ready"; detail: Onboarding.completionSummary.projectsFolder || Onboarding.projectFolder }
        ReadinessItem { Layout.fillWidth: true; name: "Content language"; statusText: Onboarding.completionSummary.contentLanguage || Onboarding.defaultContentLanguage; status: "ready"; detail: "Default for new projects" }
        ReadinessItem { Layout.fillWidth: true; name: "Theme"; statusText: Onboarding.completionSummary.theme || Onboarding.theme; status: "ready"; detail: "Can be changed in Settings" }
        ReadinessItem { Layout.fillWidth: true; name: "FFmpeg"; statusText: Onboarding.completionSummary.ffmpeg || "Needs Setup"; status: (Onboarding.completionSummary.ffmpeg === "Ready") ? "ready" : "warning"; detail: "Rendering dependency" }
        ReadinessItem { Layout.fillWidth: true; name: "Voice AI"; statusText: Onboarding.completionSummary.voiceAI || "Not installed"; status: (Onboarding.completionSummary.voiceAI === "Installed") ? "ready" : "warning"; detail: "Optional" }
        ReadinessItem { Layout.fillWidth: true; name: "Speech recognition"; statusText: Onboarding.completionSummary.speechRecognition || "Not installed"; status: (Onboarding.completionSummary.speechRecognition === "Installed") ? "ready" : "warning"; detail: "Optional" }
    }
    Text { text: "Useful shortcuts"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
    Text { Layout.fillWidth: true; text: "Space  Play/Pause    ·    Ctrl+S  Save    ·    Ctrl+B  Split    ·    Ctrl+Shift+P  Command Palette"; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
    InfoBanner { Layout.fillWidth: true; text: "Speaker = who is talking. Voice = how that speaker sounds. Autosave and local recovery are enabled." }
}
