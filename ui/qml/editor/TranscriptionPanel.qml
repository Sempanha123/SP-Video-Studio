import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    property var playbackController
    signal navigateRequested(string page, string workflow)
    signal toastRequested(string message, string variant)
    property bool advancedOpen: false
    property bool showSetup: false

    function selectedModelId() {
        if (!controller || modelCombo.currentIndex < 0 || modelCombo.currentIndex >= controller.models.length) return ""
        return controller.models[modelCombo.currentIndex].id || ""
    }

    function chooseRecommended() {
        if (!controller) return
        for (var i = 0; i < controller.models.length; i++) {
            if (controller.models[i].id === controller.recommendedModelId) {
                modelCombo.currentIndex = i
                return
            }
        }
        if (controller.models.length > 0) modelCombo.currentIndex = 0
    }

    Component.onCompleted: chooseRecommended()

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onModelsChanged() { root.chooseRecommended() }
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.md
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "Transcription"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text {
                    text: root.controller && root.controller.mediaName ? root.controller.mediaName : "Select audio or video from Media"
                    color: Theme.colors.textSecondary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.bodySmall
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }
            }
            SecondaryButton {
                text: "Open Models"
                visible: root.controller && root.controller.models.length === 0
                onClicked: root.navigateRequested("models", "")
            }
        }

        InfoBanner {
            Layout.fillWidth: true
            visible: root.controller && root.controller.mediaId !== "" && !root.controller.canTranscribe
            variant: "warning"
            text: "Images cannot be transcribed. Choose a video or audio file from Media."
        }

        AppCard {
            Layout.fillWidth: true
            visible: root.controller && root.controller.canTranscribe && (!root.controller.transcript.id || root.controller.busy || root.showSetup)
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing.lg
                spacing: Theme.spacing.md

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing.md
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Speech Recognition"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text { text: "Select the model and language, then review timestamped text after transcription."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    }
                    StatusBadge { text: root.controller ? root.controller.state.replace("_", " ") : "Idle"; status: root.controller && root.controller.busy ? "info" : "neutral" }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width < 900 ? 1 : 3
                    rowSpacing: Theme.spacing.sm
                    columnSpacing: Theme.spacing.md

                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Model"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        AppComboBox { id: modelCombo; Layout.fillWidth: true; model: root.controller ? root.controller.models : []; textRole: "name" }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Language"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        AppComboBox { id: languageCombo; Layout.fillWidth: true; model: ["Auto Detect", "English", "Khmer"] }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Device"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        AppComboBox { id: deviceCombo; Layout.fillWidth: true; model: ["Auto", "CPU", "CUDA"] }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing.lg
                    RowLayout { spacing: Theme.spacing.sm; AppSwitch { id: wordsSwitch; checked: true }; Text { text: "Word timestamps"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall } }
                    RowLayout { spacing: Theme.spacing.sm; AppSwitch { id: vadSwitch; checked: true }; Text { text: "Remove long silences"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall } }
                    Item { Layout.fillWidth: true }
                    AppButton { text: root.advancedOpen ? "Hide Advanced" : "Advanced"; variant: "ghost"; compact: true; onClicked: root.advancedOpen = !root.advancedOpen }
                }

                GridLayout {
                    visible: root.advancedOpen
                    Layout.fillWidth: true
                    columns: root.width < 900 ? 1 : 3
                    rowSpacing: Theme.spacing.sm
                    columnSpacing: Theme.spacing.md
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Compute Type"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        AppComboBox { id: computeCombo; Layout.fillWidth: true; model: ["Auto", "int8", "float16", "int8_float16", "float32"] }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Beam Size"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        AppComboBox { id: beamCombo; Layout.fillWidth: true; model: ["1", "3", "5", "8"]; currentIndex: 2 }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Mode"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        AppComboBox { id: batchCombo; Layout.fillWidth: true; model: ["Standard", "Batched"] }
                    }
                    AppTextField { id: promptField; Layout.fillWidth: true; placeholderText: "Initial prompt (optional)" }
                    AppTextField { id: hotwordsField; Layout.fillWidth: true; placeholderText: "Hotwords (optional)" }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Batch Size"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        AppComboBox { id: batchSizeCombo; Layout.fillWidth: true; model: ["2", "4", "8"]; currentIndex: 1 }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.controller && root.controller.busy
                    spacing: Theme.spacing.sm
                    Text { text: root.controller ? root.controller.statusMessage : ""; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                    ProgressBar {
                        Layout.fillWidth: true
                        from: 0; to: 1
                        indeterminate: root.controller ? !root.controller.progressKnown : true
                        value: root.controller ? root.controller.progress : 0
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    SecondaryButton { visible: root.controller && root.controller.busy; text: "Cancel"; onClicked: root.controller.cancel() }
                    AppButton {
                        visible: !root.controller || !root.controller.busy
                        text: root.controller && root.controller.transcript.id ? "Re-transcribe" : "Transcribe"
                        enabled: root.controller && root.controller.canTranscribe && modelCombo.currentIndex >= 0
                        onClicked: {
                            var languages = ["auto", "en", "km"]
                            var devices = ["auto", "cpu", "cuda"]
                            var computes = ["auto", "int8", "float16", "int8_float16", "float32"]
                            root.showSetup = false
                            root.controller.start(
                                root.selectedModelId(),
                                languages[languageCombo.currentIndex],
                                devices[deviceCombo.currentIndex],
                                wordsSwitch.checked,
                                vadSwitch.checked,
                                batchCombo.currentIndex === 1,
                                parseInt(batchSizeCombo.currentText),
                                parseInt(beamCombo.currentText),
                                computes[computeCombo.currentIndex],
                                promptField.text,
                                hotwordsField.text
                            )
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.controller && root.controller.transcript.id
            spacing: Theme.spacing.sm
            StatusBadge { text: root.controller ? root.controller.transcript.statusName : "Ready"; status: root.controller && root.controller.transcript.status === "outdated" ? "warning" : "success" }
            Text {
                text: root.controller ? ((root.controller.transcript.languageName || "Unknown") + (root.controller.transcript.languageProbabilityText ? " · " + root.controller.transcript.languageProbabilityText : "")) : ""
                color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall
            }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Re-transcribe"; compact: true; onClicked: root.showSetup = true }
            SecondaryButton { text: "Delete Transcript"; compact: true; onClicked: deleteDialog.open() }
        }

        TranscriptEditor {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.controller && root.controller.transcript.id
            controller: root.controller
            playbackController: root.playbackController
            onExportRequested: exportDialog.open()
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.controller && !root.controller.busy && !root.controller.transcript.id
            title: root.controller && root.controller.mediaId ? "No transcript yet" : "Select media to transcribe"
            description: root.controller && root.controller.mediaId ? "Choose a speech-recognition model and start transcription." : "Pick a video or audio file in Media, then open Transcription."
            actionText: ""
        }
    }

    FileDialog {
        id: exportDialog
        title: "Export Transcript"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Text Files (*.txt)"]
        onAccepted: if (root.controller) root.controller.exportTxt(selectedFile)
    }

    AppDialog {
        id: deleteDialog
        width: 440
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null
        footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { Layout.fillWidth: true; text: "Delete this transcript?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            InfoBanner { Layout.fillWidth: true; variant: "info"; text: "The timestamped transcript will be removed. Your source media will not be changed." }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: deleteDialog.close() }
                AppButton { text: "Delete"; variant: "danger"; onClicked: { if (root.controller && root.controller.deleteActiveTranscript()) deleteDialog.close() } }
            }
        }
    }
}
