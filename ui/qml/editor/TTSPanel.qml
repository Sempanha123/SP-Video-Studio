import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property var scriptController
    property var playbackController
    property string selectedSectionId: scriptController ? (scriptController.selectedSection.id || "") : ""
    property string modeCode: ["default", "designed", "reference"][modeBox.currentIndex]
    property string deviceCode: ["auto", "cpu", "cuda"][deviceBox.currentIndex]
    property bool expanded: false
    signal toastRequested(string message, string variant)

    implicitHeight: root.expanded ? panel.implicitHeight + Theme.spacing.lg * 2 : 58
    clip: true

    function cfgValue() {
        var value = Number(cfgField.text)
        return isNaN(value) ? 2.0 : value
    }
    function stepValue() {
        var value = Number(stepsField.text)
        return isNaN(value) ? 10 : Math.round(value)
    }

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
        function onPreviewReady(path, name, durationMs) {
            if (root.playbackController) root.playbackController.setExternalAudio(path, name, durationMs)
        }
    }

    Connections {
        target: root.scriptController
        ignoreUnknownSignals: true
        function onSaveStateChanged() {
            if (root.controller && root.scriptController && root.scriptController.saveState === "Saved")
                root.controller.refresh()
        }
    }

    ColumnLayout {
        id: panel
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        spacing: Theme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "Narration"
                color: Theme.colors.textPrimary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.heading
                font.weight: Theme.type.semibold
            }
            StatusBadge {
                text: root.controller && root.controller.busy ? "Working" : "VoxCPM2"
                status: root.controller && root.controller.busy ? "running" : "ready"
            }
            SecondaryButton {
                text: root.expanded ? "Collapse" : "Open"
                compact: true
                onClicked: root.expanded = !root.expanded
            }
            SecondaryButton {
                text: "Unload"
                compact: true
                visible: root.expanded
                enabled: root.controller && !root.controller.busy
                onClicked: root.controller.unloadModel()
            }
        }

        Text {
            Layout.fillWidth: true
            visible: root.expanded
            wrapMode: Text.WordWrap
            text: "Generate project narration with the installed VoxCPM2 model. Voice Studio controls arrive in the next phase."
            color: Theme.colors.textMuted
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.expanded
            spacing: Theme.spacing.md
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text { text: "Voice mode"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { id: modeBox; Layout.fillWidth: true; model: ["Default", "Designed", "Reference"] }
            }
            ColumnLayout {
                Layout.preferredWidth: 150
                spacing: 4
                Text { text: "Device"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { id: deviceBox; Layout.fillWidth: true; model: ["Auto", "CPU", "CUDA"] }
            }
        }

        AppTextField {
            id: descriptionField
            Layout.fillWidth: true
            visible: root.expanded && (root.modeCode === "designed" || root.modeCode === "reference")
            placeholderText: root.modeCode === "designed" ? "Describe the voice, tone and pacing…" : "Optional style guidance for the reference voice…"
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.expanded && root.modeCode === "reference"
            spacing: Theme.spacing.sm
            RowLayout {
                Layout.fillWidth: true
                AppTextField {
                    Layout.fillWidth: true
                    readOnly: true
                    text: root.controller ? root.controller.referencePath : ""
                    placeholderText: "Choose an authorized reference recording"
                }
                SecondaryButton { text: "Choose…"; onClicked: referenceDialog.open() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppSwitch { id: consentSwitch }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "I have permission to use this voice recording."
                    color: Theme.colors.textSecondary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.bodySmall
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.expanded
            AppSwitch { id: advancedSwitch }
            Text { text: "Advanced"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            Item { Layout.fillWidth: true }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.expanded && advancedSwitch.checked
            spacing: Theme.spacing.md
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text { text: "CFG (0.1–10)"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppTextField { id: cfgField; Layout.fillWidth: true; text: "2.0"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text { text: "Inference steps (1–100)"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppTextField { id: stepsField; Layout.fillWidth: true; text: "10"; inputMethodHints: Qt.ImhDigitsOnly }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text { text: "Seed (optional)"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppTextField { id: seedField; Layout.fillWidth: true; placeholderText: "Random"; inputMethodHints: Qt.ImhDigitsOnly }
            }
        }

        AppTextField {
            id: previewText
            Layout.fillWidth: true
            visible: root.expanded
            placeholderText: "Short preview text (up to 400 characters)"
            maximumLength: 400
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.expanded
            spacing: Theme.spacing.sm
            SecondaryButton {
                text: "Generate Preview"
                enabled: root.controller && !root.controller.busy && previewText.text.trim().length > 0
                onClicked: root.controller.generatePreview(previewText.text, root.modeCode, descriptionField.text, root.deviceCode, root.cfgValue(), root.stepValue(), seedField.text, consentSwitch.checked)
            }
            SecondaryButton {
                text: "Generate Section Voice"
                enabled: root.controller && !root.controller.busy && root.selectedSectionId !== ""
                onClicked: {
                    if (root.scriptController && !root.scriptController.save()) return
                    root.controller.generateSection(root.selectedSectionId, root.modeCode, descriptionField.text, root.deviceCode, root.cfgValue(), root.stepValue(), seedField.text, consentSwitch.checked)
                }
            }
            AppButton {
                text: "Generate Full Narration"
                iconName: "mic"
                enabled: root.controller && !root.controller.busy
                onClicked: {
                    if (root.scriptController && !root.scriptController.save()) return
                    root.controller.generateFull(root.modeCode, descriptionField.text, root.deviceCode, root.cfgValue(), root.stepValue(), seedField.text, consentSwitch.checked)
                }
            }
            SecondaryButton {
                text: "Cancel"
                visible: root.controller && root.controller.busy
                onClicked: root.controller.cancel()
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.expanded && root.controller && (root.controller.busy || root.controller.state !== "idle")
            spacing: Theme.spacing.xs
            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: root.controller ? root.controller.statusMessage : ""
                    color: Theme.colors.textSecondary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.bodySmall
                }
                Text {
                    visible: root.controller && root.controller.totalChunks > 0
                    text: root.controller ? (root.controller.currentChunk + " / " + root.controller.totalChunks) : ""
                    color: Theme.colors.textMuted
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.caption
                }
            }
            Rectangle {
                Layout.fillWidth: true
                height: 5
                radius: 3
                color: Theme.colors.border
                Rectangle {
                    width: parent.width * Math.max(0, Math.min(1, root.controller ? root.controller.progress : 0))
                    height: parent.height
                    radius: parent.radius
                    color: Theme.colors.accent
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.expanded && root.controller && !!root.controller.activeGenerated.id
            spacing: Theme.spacing.sm
            Text {
                Layout.fillWidth: true
                text: root.controller && root.controller.narrationCurrent ? "Active narration • Current" : "Active narration • Needs Update"
                color: root.controller && root.controller.narrationCurrent ? Theme.colors.success : Theme.colors.warning
                font.family: Theme.type.family
                font.pixelSize: Theme.type.bodySmall
                font.weight: Theme.type.semibold
            }
            Text {
                text: root.controller ? (root.controller.activeGenerated.durationDisplay || "") : ""
                color: Theme.colors.textMuted
                font.family: Theme.type.family
                font.pixelSize: Theme.type.caption
            }
            SecondaryButton {
                text: "Play"
                iconName: "play"
                onClicked: {
                    if (root.playbackController && root.controller)
                        root.playbackController.setExternalAudio(root.controller.activeGenerated.filePath, "Generated narration", root.controller.activeGenerated.durationMs || 0)
                }
            }
            SecondaryButton {
                text: "Remove"
                onClicked: if (root.controller) root.controller.deleteGenerated(root.controller.activeGenerated.id)
            }
        }
    }

    FileDialog {
        id: referenceDialog
        title: "Choose Reference Voice"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg *.opus *.aac)", "All Files (*.*)"]
        onAccepted: if (root.controller) root.controller.setReferencePath(selectedFile)
    }
}
