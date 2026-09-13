import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"
import SPVideoStudio.Commands 1.0

FocusScope {
    id: root
    property var controller
    property var playbackController
    signal toastRequested(string message, string variant)
    focus: true
    activeFocusOnTab: true
    Accessible.role: Accessible.Pane
    Accessible.name: "Subtitle Editor"
    Accessible.description: "Edit subtitle timing, text, style and validation warnings"
    onActiveFocusChanged: if(activeFocus && !Commands.textEditing) Commands.setContext("subtitle_editor")

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
            AppComboBox {
                id: trackPicker
                accessibleName: "Subtitle track"
                Layout.preferredWidth: 220
                model: root.controller ? root.controller.tracks : []
                textRole: "name"
                onActivated: if (root.controller && currentIndex >= 0) root.controller.loadTrack(model[currentIndex].id)
            }
            AppTextField { id: searchField; Layout.fillWidth: true; placeholderText: "Search subtitles"; tooltip: "Search subtitles"; onTextChanged: if (root.controller) root.controller.search(text) }
            AppComboBox { accessibleName: "Subtitle filter"; model: ["All", "Warnings", "Edited", "Source Changed"]; onActivated: if (root.controller) root.controller.filter(["all","warnings","edited","source_changed"][currentIndex]) }
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
                activeFocusOnTab: true
                Accessible.role: Accessible.List
                Accessible.name: "Subtitle cues"
                Keys.onUpPressed: function(event) { if (root.controller && !Commands.textEditing) { root.controller.selectRelativeCue(-1); event.accepted = true } }
                Keys.onDownPressed: function(event) { if (root.controller && !Commands.textEditing) { root.controller.selectRelativeCue(1); event.accepted = true } }
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

    AppDialog {
        id: createDialog
        initialFocusItem: kindBox
        modal: true
        width: 500
        title: "Create Subtitle Track"
        standardButtons: Dialog.Ok | Dialog.Cancel
        property string kind: "transcript"
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            AppComboBox { id: kindBox; accessibleName: "Subtitle source"; Layout.fillWidth: true; model: ["From Transcript", "From Translation", "Bilingual", "Manual"]; onActivated: createDialog.kind=["transcript","translation","bilingual","manual"][currentIndex] }
            AppComboBox { id: transcriptBox; accessibleName: "Transcript source"; Layout.fillWidth: true; visible: createDialog.kind === "transcript" || createDialog.kind === "bilingual"; model: root.controller ? root.controller.sources.transcripts : []; textRole: "label" }
            AppComboBox { id: translationBox; accessibleName: "Translation source"; Layout.fillWidth: true; visible: createDialog.kind === "translation" || createDialog.kind === "bilingual"; model: root.controller ? root.controller.sources.translations : []; textRole: "label" }
            AppComboBox { id: languageBox; accessibleName: "Subtitle language"; Layout.fillWidth: true; visible: createDialog.kind === "manual"; model: ["English", "Khmer"] }
            AppComboBox { id: presetBox; accessibleName: "Subtitle style preset"; Layout.fillWidth: true; model: root.controller ? root.controller.presetList : []; textRole: "name" }
        }
        onOpened: Commands.setModalOpen(true)
        onClosed: Commands.setModalOpen(false)
        onAccepted: {
            if (!root.controller) return
            var preset = presetBox.currentIndex >= 0 ? presetBox.model[presetBox.currentIndex].id : "clean"
            if (kind === "transcript" && transcriptBox.currentIndex >= 0) root.controller.createFromTranscript(transcriptBox.model[transcriptBox.currentIndex].id, preset)
            else if (kind === "translation" && translationBox.currentIndex >= 0) root.controller.createFromTranslation(translationBox.model[translationBox.currentIndex].id, preset)
            else if (kind === "bilingual" && transcriptBox.currentIndex >= 0 && translationBox.currentIndex >= 0) root.controller.createBilingual(transcriptBox.model[transcriptBox.currentIndex].id, translationBox.model[translationBox.currentIndex].id, preset, "source")
            else if (kind === "manual") root.controller.createManual(languageBox.currentIndex === 1 ? "km" : "en", preset)
        }
    }

    AppDialog {
        id: shiftDialog
        initialFocusItem: shiftValue
        modal: true
        onOpened: Commands.setModalOpen(true)
        onClosed: Commands.setModalOpen(false)
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
        target: Commands
        function onCommandRequested(commandId) {
            if (Commands.activeContext !== "subtitle_editor" || !root.controller) return
            if (commandId === "subtitle.commit") root.controller.flush()
            else if (commandId === "subtitle.search") { searchField.forceActiveFocus(); searchField.selectAll() }
            else if (commandId === "subtitle.split") root.controller.splitSelectedAtPlayhead()
            else if (commandId === "subtitle.delete") root.controller.deleteSelectedCue()
            else if (commandId === "subtitle.duplicate") root.controller.duplicateSelectedCue()
            else if (commandId === "general.escape") { root.forceActiveFocus(); Commands.setTextEditing(false) }
        }
    }

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
        function onPreviewReady(path) { root.toastRequested("Subtitle preview rendered", "success") }
    }
}
