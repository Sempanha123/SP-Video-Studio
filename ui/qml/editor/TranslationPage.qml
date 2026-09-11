import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import SPVideoStudio.Phase21 1.0
import "../theme"
import "../components"
import "../dubbing"

Item {
    id: root
    property var controller: null
    property var playbackController: null
    property string sourceMediaId: ""
    property bool dubMode: false
    signal navigateRequested(string page, string workflow)
    signal toastRequested(string message, string variant)

    function openDubStudio() {
        if (!root.controller) return
        Dubbing.setCurrentProject(root.controller.currentProjectId || "")
        root.dubMode = true
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.md
        visible: !root.dubMode

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; spacing: 2
                Text { text: "Translation"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Translate, review and protect human edits without changing the original transcript or script."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            }
            SecondaryButton { text: "Translate & Dub"; compact: true; onClicked: root.openDubStudio() }
            AppButton { text: "New Translation"; compact: true; onClicked: setupDialog.open() }
        }

        InfoBanner {
            Layout.fillWidth: true
            visible: root.controller && root.controller.translation.status === "outdated"
            variant: "warning"
            text: "Source content has changed since this translation was created. Sync with Source to preserve unchanged reviewed rows."
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            Text { text: "Translations"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox {
                id: documentCombo
                Layout.preferredWidth: 360
                model: root.controller ? root.controller.documents : []
                textRole: "statusName"
                onActivated: {
                    if (root.controller && currentIndex >= 0) root.controller.loadTranslation(root.controller.documents[currentIndex].id)
                }
                contentItem: Text {
                    text: documentCombo.currentIndex >= 0 && root.controller && root.controller.documents.length > documentCombo.currentIndex ?
                          (root.controller.documents[documentCombo.currentIndex].sourceLanguageName + " → " + root.controller.documents[documentCombo.currentIndex].targetLanguageName + " · " + root.controller.documents[documentCombo.currentIndex].statusName) : "Choose translation"
                    color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
                }
            }
            Item { Layout.fillWidth: true }
            Text { visible: root.controller && root.controller.busy; text: root.controller.statusMessage; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            SecondaryButton { visible: root.controller && root.controller.busy; text: "Cancel"; compact: true; onClicked: root.controller.cancel() }
        }

        ProgressBar { Layout.fillWidth: true; visible: root.controller && root.controller.busy; from: 0; to: 1; value: root.controller ? root.controller.progress : 0 }

        EmptyState {
            Layout.fillWidth: true; Layout.fillHeight: true
            visible: !root.controller || !root.controller.translation.id
            iconName: "translate"
            title: "No translation yet"
            description: "Choose a transcript or script, then translate with a local model or review manually."
            actionText: "Create Translation"
            onActionClicked: setupDialog.open()
        }

        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            visible: root.controller && !!root.controller.translation.id
            spacing: Theme.spacing.md

            TranslationInspector { Layout.fillWidth: true; translation: root.controller ? root.controller.translation : ({}) }
            TranslationToolbar {
                Layout.fillWidth: true
                controller: root.controller
                onSetupRequested: setupDialog.open()
                onExportRequested: function(bilingual) { exportDialog.bilingual = bilingual; exportDialog.open() }
                onApproveRequested: {
                    if (!root.controller) return
                    if ((root.controller.translation.reviewedCount || 0) < (root.controller.translation.segmentCount || 0)) approveDialog.open()
                    else root.controller.approve(false)
                }
            }

            ListView {
                id: translationList
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true
                spacing: Theme.spacing.md
                model: root.controller ? root.controller.segments : null
                ScrollBar.vertical: ScrollBar {}
                delegate: TranslationSegmentRow {
                    width: translationList.width
                    segmentId: model.segmentId
                    sourceText: model.sourceText
                    translatedText: model.translatedText
                    timeText: model.timeText
                    startMs: model.startMs
                    statusName: model.statusName
                    reviewed: model.reviewed
                    locked: model.locked
                    edited: model.edited
                    orphaned: model.orphaned
                    qualityWarnings: model.qualityWarnings
                    onTextEdited: function(id, text) { root.controller.queueEdit(id, text) }
                    onReviewedChanged: function(id, value) { root.controller.markReviewed(id, value) }
                    onLockedChanged: function(id, value) { root.controller.setLocked(id, value) }
                    onResetRequested: function(id) { root.controller.resetSegment(id) }
                    onRetranslateRequested: function(id, replaceManual) { root.controller.retranslateSegment(id, replaceManual) }
                    onPlayRequested: function(start) {
                        var tr = root.controller.translation
                        if (tr.source_type === "transcript") {
                            var docs = root.controller.sources
                            for (var i = 0; i < docs.length; i++) if (docs[i].id === tr.source_id) root.controller.playSource(docs[i].mediaId || "", start, true)
                        }
                    }
                }
            }
            TranslationStatsBar { Layout.fillWidth: true; translation: root.controller ? root.controller.translation : ({}); saveState: root.controller ? root.controller.saveState : "Saved" }
        }
    }

    TranslateDubStudio {
        anchors.fill: parent
        visible: root.dubMode
        controller: Dubbing
        onNavigateRequested: function(mode) {
            if (mode === "translation") { root.dubMode = false; return }
            if (mode === "voice") { root.navigateRequested("voices", ""); return }
            root.toastRequested("Use the project workspace tabs to open " + mode + ".", "info")
        }
    }

    TranslationSetupDialog { id: setupDialog; controller: root.controller }

    FileDialog {
        id: exportDialog
        property bool bilingual: false
        title: bilingual ? "Export Bilingual Translation" : "Export Translation"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Text Files (*.txt)"]
        defaultSuffix: "txt"
        onAccepted: if (root.controller) root.controller.exportTxt(selectedFile.toString(), bilingual)
    }

    AppDialog {
        id: approveDialog
        width: 470; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Approve with unreviewed segments?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; text: ((root.controller ? root.controller.translation.segmentCount - root.controller.translation.reviewedCount : 0) + " segments have not been reviewed."); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Continue Reviewing"; onClicked: approveDialog.close() }; AppButton { text: "Approve Anyway"; onClicked: { approveDialog.close(); root.controller.approve(true) } } }
        }
    }

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
        function onContextChanged() { if (root.dubMode && root.controller) Dubbing.setCurrentProject(root.controller.currentProjectId || "") }
    }

    Connections {
        target: Dubbing
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
        function onPreviewRequested(mode) {
            if (!root.playbackController) return
            var paths=Dubbing.previewPaths || ({})
            if (mode === "original") {
                if (paths.sourceMediaId) { root.playbackController.setMedia(paths.sourceMediaId); root.playbackController.play() }
                return
            }
            var path=mode === "dub" ? (paths.dub || "") : (paths.mixed || "")
            if (path) { root.playbackController.setExternalAudio(path, mode === "dub" ? "Dub Only" : "Dubbed Mix", Number(paths.durationMs || 0)); root.playbackController.play() }
            else root.toastRequested("Rebuild the dubbed audio mix first.", "warning")
        }
    }
}
