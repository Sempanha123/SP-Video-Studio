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
    signal toastRequested(string message, string variant)

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.md

        SubtitleToolbar {
            Layout.fillWidth: true
            controller: root.controller
            onCreateRequested: createDialog.open()
            onImportRequested: importDialog.open()
            onExportRequested: exportDialog.open()
            onRenderPreviewRequested: if (root.controller) root.controller.renderPreview()
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            ComboBox {
                id: trackPicker
                Layout.preferredWidth: 220
                model: root.controller ? root.controller.tracks : []
                textRole: "name"
                onActivated: if (root.controller && currentIndex >= 0) root.controller.loadTrack(model[currentIndex].id)
            }
            TextField { id: searchField; Layout.fillWidth: true; placeholderText: "Search subtitles"; onTextChanged: if (root.controller) root.controller.search(text) }
            ComboBox { model: ["All", "Warnings", "Edited", "Source Changed"]; onActivated: if (root.controller) root.controller.filter(["all","warnings","edited","source_changed"][currentIndex]) }
            SecondaryButton { text: "Shift"; compact: true; enabled: !!root.controller && !!root.controller.track.id; onClicked: shiftDialog.open() }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.md
            Text { text: root.controller && root.controller.track.id ? (root.controller.track.language || "").toUpperCase() + " • " + root.controller.cueCount + " cues" : "No subtitle track"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            Item { Layout.fillWidth: true }
            Text { text: root.controller ? root.controller.validationSummary.errors + " errors • " + root.controller.validationSummary.warnings + " warnings" : ""; color: root.controller && root.controller.validationSummary.errors > 0 ? Theme.colors.danger : Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: root.width < 900 ? Qt.Vertical : Qt.Horizontal

            ListView {
                id: cueList
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: 420
                clip: true
                spacing: Theme.spacing.sm
                model: root.controller ? root.controller.cues : null
                ScrollBar.vertical: ScrollBar {}
                delegate: SubtitleCueRow {
                    width: cueList.width - (cueList.ScrollBar.vertical ? 12 : 0)
                    controller: root.controller
                    cueId: model.cueId
                    startMs: model.startMs
                    endMs: model.endMs
                    timeText: model.timeText
                    cueText: model.cueText
                    secondaryText: model.secondaryText
                    edited: model.edited
                    activeCue: model.active
                    sourceChanged: model.sourceChanged
                    sourceMissing: model.sourceMissing
                    warning: model.warning
                    onSelectRequested: function(id) { if (root.controller) root.controller.selectCue(id) }
                }
            }

            SubtitleStylePanel {
                SplitView.preferredWidth: 270
                SplitView.minimumWidth: 240
                SplitView.fillHeight: true
                controller: root.controller
            }
        }
    }

    Dialog {
        id: createDialog
        modal: true
        width: 500
        title: "Create Subtitle Track"
        standardButtons: Dialog.Ok | Dialog.Cancel
        property string kind: "transcript"
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            ComboBox { id: kindBox; Layout.fillWidth: true; model: ["From Transcript", "From Translation", "Bilingual", "Manual"]; onActivated: createDialog.kind=["transcript","translation","bilingual","manual"][currentIndex] }
            ComboBox { id: transcriptBox; Layout.fillWidth: true; visible: createDialog.kind === "transcript" || createDialog.kind === "bilingual"; model: root.controller ? root.controller.sources.transcripts : []; textRole: "label" }
            ComboBox { id: translationBox; Layout.fillWidth: true; visible: createDialog.kind === "translation" || createDialog.kind === "bilingual"; model: root.controller ? root.controller.sources.translations : []; textRole: "label" }
            ComboBox { id: languageBox; Layout.fillWidth: true; visible: createDialog.kind === "manual"; model: ["English", "Khmer"] }
            ComboBox { id: presetBox; Layout.fillWidth: true; model: root.controller ? root.controller.presetList : []; textRole: "name" }
        }
        onAccepted: {
            if (!root.controller) return
            var preset = presetBox.currentIndex >= 0 ? presetBox.model[presetBox.currentIndex].id : "clean"
            if (kind === "transcript" && transcriptBox.currentIndex >= 0) root.controller.createFromTranscript(transcriptBox.model[transcriptBox.currentIndex].id, preset)
            else if (kind === "translation" && translationBox.currentIndex >= 0) root.controller.createFromTranslation(translationBox.model[translationBox.currentIndex].id, preset)
            else if (kind === "bilingual" && transcriptBox.currentIndex >= 0 && translationBox.currentIndex >= 0) root.controller.createBilingual(transcriptBox.model[transcriptBox.currentIndex].id, translationBox.model[translationBox.currentIndex].id, preset, "source")
            else if (kind === "manual") root.controller.createManual(languageBox.currentIndex === 1 ? "km" : "en", preset)
        }
    }

    Dialog {
        id: shiftDialog
        modal: true
        title: "Shift All Subtitles"
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: RowLayout { Text { text: "Milliseconds" }; SpinBox { id: shiftValue; from: -60000; to: 60000; value: 500; editable: true } }
        onAccepted: if (root.controller) root.controller.shiftAll(shiftValue.value)
    }

    FileDialog {
        id: importDialog
        title: "Import Subtitles"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Subtitle Files (*.srt *.vtt *.ass)"]
        onAccepted: if (root.controller) root.controller.importSubtitle(selectedFile, "en", "clean")
    }

    FileDialog {
        id: exportDialog
        title: "Export Subtitles"
        fileMode: FileDialog.SaveFile
        nameFilters: ["SubRip (*.srt)", "WebVTT (*.vtt)", "Advanced SubStation Alpha (*.ass)"]
        onAccepted: if (root.controller) root.controller.exportTrack(selectedNameFilter.indexOf("WebVTT") >= 0 ? "vtt" : selectedNameFilter.indexOf("Advanced") >= 0 ? "ass" : "srt", selectedFile)
    }

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
        function onPreviewReady(path) { root.toastRequested("Subtitle preview rendered", "success") }
    }
}
