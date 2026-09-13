import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import SPVideoStudio.Phase29 1.0
import SPVideoStudio.Phase31 1.0
import "../theme"
import "../components"
import "../storage"
import "../accessibility"
import "../privacy"

Item {
    id: root
    property string section: "General"
    signal navigateRequested(string page, string context)

    function readiness() {
        return typeof readinessController !== "undefined" ? readinessController.readiness : ({})
    }

    FolderDialog {
        id: projectFolderDialog
        title: "Choose default projects folder"
        onAccepted: {
            if (typeof settingsController !== "undefined")
                settingsController.setProjectFolder(selectedFolder.toString())
        }
    }

    FileDialog {
        id: ffmpegDialog
        title: "Locate FFmpeg executable"
        fileMode: FileDialog.OpenFile
        nameFilters: Qt.platform.os === "windows" ? ["FFmpeg executable (ffmpeg.exe)", "Executables (*.exe)"] : ["FFmpeg executable (ffmpeg)", "All files (*)"]
        onAccepted: {
            if (typeof settingsController !== "undefined")
                settingsController.setCustomFFmpeg(selectedFile.toString())
        }
    }

    AppDialog {
        id: resetDialog
        width: 460
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null
        footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Reset application settings?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; text: "This restores settings to safe defaults. Projects, media and AI models will not be deleted."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: resetDialog.close() }
                AppButton {
                    text: "Reset"
                    variant: "danger"
                    onClicked: {
                        settingsController.resetSettings()
                        resetDialog.close()
                    }
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spacing.xl

        AppCard {
            Layout.preferredWidth: 210
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing.md
                spacing: Theme.spacing.xs
                Text {
                    text: "Settings"
                    color: Theme.colors.textPrimary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.title
                    font.weight: Theme.type.semibold
                    Layout.leftMargin: Theme.spacing.sm
                    Layout.topMargin: Theme.spacing.sm
                    Layout.bottomMargin: Theme.spacing.sm
                }
                Repeater {
                    model: ["General", "Appearance", "Projects", "Performance", "Rendering", "Keyboard Shortcuts", "Accessibility", "Privacy", "Storage", "Advanced"]
                    delegate: SidebarItem {
                        required property string modelData
                        Layout.fillWidth: true
                        text: modelData
                        iconName: modelData === "Appearance" ? "theme" : (modelData === "Projects" ? "projects" : "settings")
                        selected: root.section === modelData
                        onClicked: root.section = modelData
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: Theme.spacing.lg

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: root.section; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                    Text {
                        text: {
                            if (root.section === "General") return "Language and startup behavior."
                            if (root.section === "Appearance") return "Choose how SP Video Studio looks on your desktop."
                            if (root.section === "Projects") return "Choose where new projects are created."
                            if (root.section === "Performance") return "Tune performance and review system readiness."
                            if (root.section === "Rendering") return "Set defaults for future rendering workflows."
                            if (root.section === "Keyboard Shortcuts") return "Search, customize and reset keyboard shortcuts safely."
                            if (root.section === "Accessibility") return "Motion, text size and keyboard focus preferences."
                            if (root.section === "Privacy") return "Review local and online processing, support-bundle boundaries and sensitive voice handling."
                            if (root.section === "Storage") return "Review storage usage, safe cache cleanup and disk health."
                            return "Diagnostics and advanced application preferences."
                        }
                        color: Theme.colors.textSecondary
                        font.family: Theme.type.family
                        font.pixelSize: Theme.type.body
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                SettingsSection {
                    visible: root.section === "General"
                    Layout.fillWidth: true
                    title: "Application"
                    description: "These preferences are saved automatically and restored on startup."
                    SettingsRow {
                        title: "Application language"
                        description: "UI localization architecture is prepared for English and Khmer."
                        RowLayout {
                            spacing: Theme.spacing.sm
                            RadioCard { Layout.preferredWidth: 132; implicitHeight: 56; title: "English"; value: "en"; selected: settingsController.language === "en"; onChosen: settingsController.setLanguage(value) }
                            RadioCard { Layout.preferredWidth: 132; implicitHeight: 56; title: "Khmer"; value: "km"; selected: settingsController.language === "km"; onChosen: settingsController.setLanguage(value) }
                        }
                    }
                    SettingsRow {
                        title: "Open last project on startup"
                        description: "Prepared for the startup flow; no project is opened automatically yet."
                        AppSwitch { checked: settingsController.openLastProject; onToggled: settingsController.setOpenLastProject(checked) }
                    }
                    SettingsRow {
                        title: "Show Home on startup"
                        description: "Keep the welcome dashboard as the default startup destination."
                        AppSwitch { checked: settingsController.showWelcomeHome; onToggled: settingsController.setShowWelcomeHome(checked) }
                    }
                }

                SettingsSection {
                    visible: root.section === "Appearance"
                    Layout.fillWidth: true
                    title: "Theme"
                    description: "Theme changes apply immediately and persist across restarts."
                    GridLayout {
                        Layout.fillWidth: true
                        columns: width < 650 ? 1 : 3
                        columnSpacing: Theme.spacing.md
                        rowSpacing: Theme.spacing.md
                        RadioCard { Layout.fillWidth: true; title: "System"; description: "Follow Windows appearance"; value: "system"; selected: settingsController.theme === value; onChosen: settingsController.setTheme(value) }
                        RadioCard { Layout.fillWidth: true; title: "Light"; description: "Bright, calm workspace"; value: "light"; selected: settingsController.theme === value; onChosen: settingsController.setTheme(value) }
                        RadioCard { Layout.fillWidth: true; title: "Dark"; description: "Comfortable low-light UI"; value: "dark"; selected: settingsController.theme === value; onChosen: settingsController.setTheme(value) }
                    }
                }

                SettingsSection {
                    visible: root.section === "Projects"
                    Layout.fillWidth: true
                    title: "Default Projects Folder"
                    description: "Changing this location affects newly created projects only."
                    PathSelector {
                        path: settingsController.projectFolder
                        onBrowseRequested: projectFolderDialog.open()
                        onResetRequested: settingsController.resetProjectFolder()
                    }
                    InfoBanner { Layout.fillWidth: true; text: "Existing projects will remain in their current locations." }
                }

                SettingsSection {
                    visible: root.section === "Performance"
                    Layout.fillWidth: true
                    title: "Performance Profile"
                    description: "Profiles now control preview resources, background work and heavy-model lifecycle without changing final render quality."
                    GridLayout {
                        Layout.fillWidth: true
                        columns: width < 650 ? 1 : 2
                        columnSpacing: Theme.spacing.md
                        rowSpacing: Theme.spacing.md
                        RadioCard { Layout.fillWidth: true; title: "Auto"; description: "Adapt to detected hardware"; value: "auto"; selected: settingsController.performanceProfile === value; onChosen: { settingsController.setPerformanceProfile(value); Performance.setProfile(value) } }
                        RadioCard { Layout.fillWidth: true; title: "Low Memory"; description: "Lower memory and concurrency"; value: "low_memory"; selected: settingsController.performanceProfile === value; onChosen: { settingsController.setPerformanceProfile(value); Performance.setProfile(value) } }
                        RadioCard { Layout.fillWidth: true; title: "Balanced"; description: "Moderate quality and caching"; value: "balanced"; selected: settingsController.performanceProfile === value; onChosen: { settingsController.setPerformanceProfile(value); Performance.setProfile(value) } }
                        RadioCard { Layout.fillWidth: true; title: "Maximum Quality"; description: "Prefer quality when hardware allows"; value: "maximum_quality"; selected: settingsController.performanceProfile === value; onChosen: { settingsController.setPerformanceProfile(value); Performance.setProfile(value) } }
                    }
                }

                SettingsSection {
                    visible: root.section === "Performance"
                    Layout.fillWidth: true
                    title: "Preview & Background Work"
                    description: "Editor preview may use lighter temporary resources under load. Export quality is never reduced."
                    SettingsRow {
                        title: "Preview Quality"
                        description: "Auto adapts to scene complexity; Performance uses lighter preview resources; Quality favors editor fidelity."
                        AppComboBox {
                            Layout.preferredWidth: 180
                            model: ["Auto", "Performance", "Quality"]
                            Component.onCompleted: currentIndex = Math.max(0, ["auto","performance","quality"].indexOf(Performance.previewQuality))
                            onActivated: Performance.setPreviewQuality(String(currentText).toLowerCase())
                        }
                    }
                    SettingsRow {
                        title: "Background Worker Limit"
                        description: "Advanced cap for metadata, cache and interactive background tasks. Heavy AI/render stages keep their own stricter limits."
                        SpinBox { from: 1; to: 16; value: Performance.workerLimit; onValueModified: Performance.setWorkerLimit(value) }
                    }
                    SettingsRow {
                        title: "Effective profile"
                        description: "Auto resolves once from available memory and CPU; explicit choices stay fixed."
                        StatusBadge { text: Performance.effectiveProfile.replaceAll("_"," "); status: "ready" }
                    }
                }

                SettingsSection {
                    visible: root.section === "Performance"
                    Layout.fillWidth: true
                    title: "System Readiness"
                    description: readinessController.checking ? "Checking hardware and media tools..." : (root.readiness().lastCheckedAt ? "Best-effort hardware and software detection." : "Run a check to inspect this computer.")
                    RowLayout {
                        Layout.fillWidth: true
                        StatusBadge {
                            text: readinessController.checking ? "Checking" : (root.readiness().overallDisplay || "Not checked")
                            status: readinessController.checking ? "checking" : (root.readiness().overallStatus || "unknown")
                        }
                        Item { Layout.fillWidth: true }
                        SecondaryButton { text: "Recheck System"; enabled: !readinessController.checking; onClicked: readinessController.recheck() }
                    }
                    Text { text: "System"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.label; font.weight: Theme.type.semibold }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: width < 680 ? 1 : 2
                        columnSpacing: Theme.spacing.md
                        rowSpacing: Theme.spacing.md
                        ReadinessItem { Layout.fillWidth: true; name: "Operating System"; statusText: (root.readiness().os && root.readiness().os !== "Unknown") ? "Detected" : "Unknown"; status: (root.readiness().os && root.readiness().os !== "Unknown") ? "ready" : "unknown"; detail: (root.readiness().os || "Unknown") + " " + (root.readiness().osVersion || "") + " · " + (root.readiness().architecture || "Unknown") }
                        ReadinessItem { Layout.fillWidth: true; name: "CPU"; statusText: (root.readiness().cpuName && root.readiness().cpuName !== "Unknown") ? "Detected" : "Unknown"; status: (root.readiness().cpuName && root.readiness().cpuName !== "Unknown") ? "ready" : "unknown"; detail: (root.readiness().cpuName || "Unknown") + " · " + (root.readiness().cpuLogicalCores || "?") + " logical cores" }
                        ReadinessItem { Layout.fillWidth: true; name: "Memory"; statusText: root.readiness().ramTotal ? "Ready" : "Unknown"; status: root.readiness().ramTotal ? "ready" : "unknown"; detail: (root.readiness().ramTotalDisplay || "Unknown") + " total · " + (root.readiness().ramAvailableDisplay || "Unknown") + " available" }
                    }

                    Text { text: "Graphics"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.label; font.weight: Theme.type.semibold }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: width < 680 ? 1 : 2
                        columnSpacing: Theme.spacing.md
                        rowSpacing: Theme.spacing.md
                        ReadinessItem { Layout.fillWidth: true; name: "GPU"; statusText: root.readiness().gpuStatus === "ready" ? "Detected" : "Unknown"; status: root.readiness().gpuStatus || "unknown"; detail: (root.readiness().gpuName || "Detection unavailable") + (root.readiness().gpuMemoryTotal ? " · " + root.readiness().gpuMemoryTotalDisplay + " VRAM" : "") }
                        ReadinessItem { Layout.fillWidth: true; name: "CUDA"; statusText: root.readiness().cudaStatusDisplay || "Unknown"; status: root.readiness().cudaStatus || "unknown"; detail: "Version " + (root.readiness().cudaVersion || "Unknown") }
                    }

                    Text { text: "Media Tools"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.label; font.weight: Theme.type.semibold }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: width < 680 ? 1 : 2
                        columnSpacing: Theme.spacing.md
                        rowSpacing: Theme.spacing.md
                        ReadinessItem { Layout.fillWidth: true; name: "FFmpeg"; statusText: root.readiness().ffmpegAvailable ? "Ready" : "Missing"; status: root.readiness().ffmpegAvailable ? "ready" : "setup-required"; detail: root.readiness().ffmpegAvailable ? ((root.readiness().ffmpegVersion || "Unknown") + " · " + (root.readiness().ffmpegPath || "")) : "Required for future media operations" }
                        ReadinessItem { Layout.fillWidth: true; name: "FFprobe"; statusText: root.readiness().ffprobeAvailable ? "Ready" : "Missing"; status: root.readiness().ffprobeAvailable ? "ready" : "setup-required"; detail: root.readiness().ffprobeAvailable ? ((root.readiness().ffprobeVersion || "Unknown") + " · " + (root.readiness().ffprobePath || "")) : "Required for future media inspection" }
                    }

                    Text { text: "AI Models"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.label; font.weight: Theme.type.semibold }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: width < 680 ? 1 : 2
                        columnSpacing: Theme.spacing.md
                        rowSpacing: Theme.spacing.md
                        ReadinessItem { Layout.fillWidth: true; name: "VoxCPM2"; statusText: root.readiness().voxcpmStatus === "installed" ? "Installed" : "Not Installed"; status: root.readiness().voxcpmStatus || "not-installed"; detail: "Text-to-Speech model" }
                        ReadinessItem { Layout.fillWidth: true; name: "faster-whisper"; statusText: root.readiness().whisperStatus === "installed" ? "Installed" : "Not Installed"; status: root.readiness().whisperStatus || "not-installed"; detail: "Speech-to-Text model" }
                    }

                    Text { text: "Storage"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.label; font.weight: Theme.type.semibold }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: width < 680 ? 1 : 2
                        columnSpacing: Theme.spacing.md
                        rowSpacing: Theme.spacing.md
                        Repeater {
                            model: root.readiness().disks || []
                            delegate: ReadinessItem {
                                required property var modelData
                                Layout.fillWidth: true
                                name: modelData.name
                                statusText: modelData.status === "ready" ? "Ready" : (modelData.status === "critical" ? "Critical" : (modelData.status === "warning" ? "Low Space" : "Unknown"))
                                status: modelData.status
                                detail: modelData.detail + " · " + modelData.path
                            }
                        }
                    }
                    InfoBanner {
                        visible: (root.readiness().warnings || []).length > 0
                        Layout.fillWidth: true
                        variant: "warning"
                        text: (root.readiness().warnings || []).join("  •  ")
                    }
                }

                SettingsSection {
                    visible: root.section === "Performance"
                    Layout.fillWidth: true
                    title: "FFmpeg Discovery"
                    description: "Auto Detect checks PATH. A custom executable is validated before it is saved."
                    SettingsRow {
                        title: "Discovery mode"
                        description: settingsController.ffmpegMode === "custom" ? "Using a validated custom executable." : "Automatically detect FFmpeg and FFprobe."
                        RowLayout {
                            spacing: Theme.spacing.sm
                            StatusBadge { text: settingsController.ffmpegMode === "custom" ? "Custom" : "Auto Detect"; status: "ready" }
                            SecondaryButton { text: "Auto Detect"; compact: true; enabled: !settingsController.mediaToolValidating; onClicked: settingsController.useAutoDetectedFFmpeg() }
                            SecondaryButton { text: settingsController.mediaToolValidating ? "Validating..." : "Browse..."; compact: true; enabled: !settingsController.mediaToolValidating; onClicked: ffmpegDialog.open() }
                        }
                    }
                    Text {
                        visible: settingsController.ffmpegPath.length > 0
                        Layout.fillWidth: true
                        text: "FFmpeg: " + settingsController.ffmpegPath + (settingsController.ffprobePath.length > 0 ? "\nFFprobe: " + settingsController.ffprobePath : "")
                        color: Theme.colors.textMuted
                        font.family: Theme.type.family
                        font.pixelSize: Theme.type.caption
                        wrapMode: Text.WrapAnywhere
                    }
                }

                SettingsSection {
                    visible: root.section === "Rendering"
                    Layout.fillWidth: true
                    title: "Rendering Defaults"
                    description: "These values prepare future project/rendering workflows; rendering is not implemented in this phase."
                    SettingsRow {
                        title: "Default FPS"
                        AppComboBox {
                            Layout.preferredWidth: 150
                            model: [24, 25, 30, 50, 60]
                            Component.onCompleted: currentIndex = model.indexOf(settingsController.defaultFps)
                            onActivated: settingsController.setDefaultFps(currentValue)
                        }
                    }
                    SettingsRow {
                        title: "Default aspect ratio"
                        AppComboBox {
                            Layout.preferredWidth: 150
                            model: ["9:16", "16:9", "1:1"]
                            Component.onCompleted: currentIndex = model.indexOf(settingsController.defaultAspectRatio)
                            onActivated: settingsController.setDefaultAspectRatio(currentValue)
                        }
                    }
                    SettingsRow {
                        title: "Preferred encoder"
                        description: "Hardware encoder discovery arrives with the rendering phase."
                        StatusBadge { text: "Auto"; status: "ready" }
                    }
                }

                SettingsSection {
                    visible: root.section === "Keyboard Shortcuts"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 620
                    title: "Keyboard Shortcuts"
                    description: "Mouse actions remain available. Conflicts are detected only where shortcut contexts overlap."
                    Loader { Layout.fillWidth: true; Layout.fillHeight: true; source: Qt.resolvedUrl("../shortcuts/ShortcutSettings.qml") }
                }

                SettingsSection {
                    visible: root.section === "Accessibility"
                    Layout.fillWidth: true
                    title: "Accessibility"
                    description: "Preferences apply immediately and persist across restarts. They do not change project or export content."
                    SettingsRow {
                        title: "Reduce Motion"
                        description: "Minimize non-essential fades, hover lift and panel animation while keeping progress feedback visible."
                        RowLayout {
                            spacing: Theme.spacing.sm
                            RadioCard { Layout.preferredWidth: 154; implicitHeight: 62; title: "Follow System"; value: "system"; selected: settingsController.reduceMotionMode === value; onChosen: settingsController.setReduceMotion(value) }
                            RadioCard { Layout.preferredWidth: 112; implicitHeight: 62; title: "On"; value: "on"; selected: settingsController.reduceMotionMode === value; onChosen: settingsController.setReduceMotion(value) }
                            RadioCard { Layout.preferredWidth: 112; implicitHeight: 62; title: "Off"; value: "off"; selected: settingsController.reduceMotionMode === value; onChosen: settingsController.setReduceMotion(value) }
                        }
                    }
                    SettingsRow {
                        title: "Interface Text Size"
                        description: "Large increases shared UI typography modestly without turning the compact desktop layout into an oversized interface."
                        RowLayout {
                            spacing: Theme.spacing.sm
                            RadioCard { Layout.preferredWidth: 150; implicitHeight: 62; title: "Default"; value: "default"; selected: settingsController.interfaceTextSize === value; onChosen: settingsController.setInterfaceTextSize(value) }
                            RadioCard { Layout.preferredWidth: 150; implicitHeight: 62; title: "Large"; value: "large"; selected: settingsController.interfaceTextSize === value; onChosen: settingsController.setInterfaceTextSize(value) }
                        }
                    }
                    SettingsRow {
                        title: "Stronger Focus Indicator"
                        description: "Use a slightly thicker soft-accent outline for keyboard focus. Selection remains a separate state."
                        AppSwitch { accessibleName: "Stronger Focus Indicator"; checked: settingsController.strongerFocusIndicator; onToggled: settingsController.setStrongerFocusIndicator(checked) }
                    }
                    AccessibilityPreview { Layout.fillWidth: true }
                    InfoBanner { Layout.fillWidth: true; text: settingsController.reduceMotionMode === "system" ? "Follow System uses Windows animation preference when available and otherwise keeps normal motion." : "Reduced motion affects interface animation only; media playback and essential progress remain unchanged." }
                }

                PrivacySettingsPanel {
                    visible: root.section === "Privacy"
                    Layout.fillWidth: true
                    onNavigateRequested: function(page, context) { root.navigateRequested(page, context) }
                }

                StoragePage {
                    visible: root.section === "Storage"
                    Layout.fillWidth: true
                    controller: Storage
                }

                SettingsSection {
                    visible: root.section === "Advanced"
                    Layout.fillWidth: true
                    title: "Diagnostics"
                    description: "Safe diagnostic options only. Secrets are never included in logs."
                    SettingsRow {
                        title: "Enable debug logging"
                        description: "Increase diagnostic log detail without restarting the app."
                        AppSwitch { checked: settingsController.debugLogging; onToggled: settingsController.setDebugLogging(checked) }
                    }
                    SettingsRow {
                        title: "Show technical error details"
                        description: "Allow future error dialogs to include optional technical details."
                        AppSwitch { checked: settingsController.showTechnicalDetails; onToggled: settingsController.setShowTechnicalDetails(checked) }
                    }
                    SettingsRow {
                        title: "Check readiness on startup"
                        description: "Run one background readiness check after the app opens."
                        AppSwitch { checked: settingsController.readinessOnStartup; onToggled: settingsController.setReadinessOnStartup(checked) }
                    }
                }

                SettingsSection {
                    visible: root.section === "Advanced"
                    Layout.fillWidth: true
                    title: "Reset Settings"
                    description: "Reset preferences without deleting projects, media, models, or the project database."
                    RowLayout {
                        Layout.fillWidth: true
                        Item { Layout.fillWidth: true }
                        AppButton { text: "Reset Settings"; variant: "danger"; onClicked: resetDialog.open() }
                    }
                }

                Item { Layout.preferredHeight: Theme.spacing.xs }
            }
        }
    }
}
