import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    property var ttsController
    property var playbackController
    property bool syncingText: false
    property string pendingDeleteId: ""
    property string pendingDeleteTitle: ""
    property int pendingDeleteMetric: 0
    signal toastRequested(string message, string variant)

    function syncEditor() {
        if (!controller) return
        root.syncingText = true
        editor.text = controller.selectedSection.content || ""
        notesField.text = controller.selectedSection.notes || ""
        root.syncingText = false
        editor.forceActiveFocus()
        editor.cursorPosition = editor.length
    }

    Component.onCompleted: if (controller) root.syncEditor()
    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onSelectedSectionChanged() { root.syncEditor() }
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
    }

    Shortcut { sequence: StandardKey.Save; onActivated: if (root.controller) root.controller.save() }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.md
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                Text { text: "Script"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                Text { text: "Write narration in reusable sections. Duration is an estimate until voice is generated."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
            Text { text: "Language"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox {
                Layout.preferredWidth: 125
                model: ["English", "Khmer"]
                currentIndex: root.controller && root.controller.script.language === "km" ? 1 : 0
                onActivated: if (root.controller) root.controller.setLanguage(currentIndex === 1 ? "km" : "en")
            }
            Text { text: "Pace"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox {
                Layout.preferredWidth: 112
                model: ["Slow", "Normal", "Fast"]
                currentIndex: !root.controller ? 1 : (root.controller.script.pace === "slow" ? 0 : (root.controller.script.pace === "fast" ? 2 : 1))
                onActivated: if (root.controller) root.controller.setPace(["slow", "normal", "fast"][currentIndex])
            }
        }

        ScriptToolbar {
            Layout.fillWidth: true
            controller: root.controller
            editor: editor
            onImportRequested: importDialog.open()
            onExportRequested: exportDialog.open()
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            AppCard {
                SplitView.preferredWidth: 270
                SplitView.minimumWidth: 220
                SplitView.maximumWidth: 360
                SplitView.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacing.md
                    spacing: Theme.spacing.sm
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Outline"; Layout.fillWidth: true; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                        AppButton { text: "+ Add"; compact: true; variant: "ghost"; onClicked: { addTitle.text = ""; addDialog.open(); addTitle.forceActiveFocus() } }
                    }
                    ListView {
                        id: outline
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Theme.spacing.xs
                        clip: true
                        model: root.controller ? root.controller.sections : null
                        delegate: Rectangle {
                            required property string sectionId
                            required property int sectionOrder
                            required property string title
                            required property string preview
                            required property bool sectionEnabled
                            required property string metric
                            required property string durationText
                            required property bool selected
                            required property bool sceneSource
                            width: ListView.view.width
                            height: 92
                            radius: Theme.radius.medium
                            color: selected ? Theme.colors.accentSoft : (hover.hovered ? Theme.colors.surfaceHover : "transparent")
                            border.color: selected ? Theme.colors.accent : Theme.colors.border
                            opacity: sectionEnabled ? 1 : 0.58
                            HoverHandler { id: hover }
                            TapHandler { onTapped: if (root.controller) root.controller.selectSection(sectionId) }
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: Theme.spacing.sm; spacing: 3
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: title; Layout.fillWidth: true; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold; elide: Text.ElideRight }
                                    AppSwitch { checked: sectionEnabled; onToggled: if (root.controller) root.controller.setSectionEnabled(sectionId, checked) }
                                }
                                Text { Layout.fillWidth: true; text: preview || "Empty section"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; elide: Text.ElideRight }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: metric + " • " + durationText; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: 10 }
                                    AppButton { text: sceneSource ? "Scene ✓" : "Scene"; compact: true; variant: sceneSource ? "secondary" : "ghost"; onClicked: if (root.controller) root.controller.setSceneSource(sectionId, !sceneSource) }
                                    Item { Layout.fillWidth: true }
                                    AppButton { text: "↑"; compact: true; variant: "ghost"; enabled: sectionOrder > 0; onClicked: if (root.controller) root.controller.moveSection(sectionId, sectionOrder - 1) }
                                    AppButton { text: "↓"; compact: true; variant: "ghost"; onClicked: if (root.controller) root.controller.moveSection(sectionId, sectionOrder + 1) }
                                }
                            }
                        }
                    }
                }
            }

            AppCard {
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: 440
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacing.lg
                    spacing: Theme.spacing.md
                    RowLayout {
                        Layout.fillWidth: true
                        AppTextField {
                            id: titleField
                            Layout.fillWidth: true
                            text: root.controller ? (root.controller.selectedSection.title || "") : ""
                            placeholderText: "Section title"
                            onEditingFinished: if (root.controller && root.controller.selectedSection.id) root.controller.renameSection(root.controller.selectedSection.id, text)
                        }
                        SecondaryButton { text: "Duplicate"; iconName: "copy"; compact: true; enabled: root.controller && !!root.controller.selectedSection.id; onClicked: root.controller.duplicateSection(root.controller.selectedSection.id) }
                        SecondaryButton {
                            text: "Delete"; iconName: "trash"; compact: true; enabled: root.controller && !!root.controller.selectedSection.id
                            onClicked: {
                                var s = root.controller.selectedSection
                                var analysis = root.controller.analysis
                                root.pendingDeleteId = s.id || ""; root.pendingDeleteTitle = s.title || "section"; root.pendingDeleteMetric = analysis.metricValue || 0
                                if ((s.content || "").trim().length > 0) deleteDialog.open()
                                else root.controller.deleteSection(root.pendingDeleteId)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radius.medium
                        color: Theme.colors.surfaceRaised
                        border.color: editor.activeFocus ? Theme.colors.accent : Theme.colors.border
                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 1
                            TextArea {
                                id: editor
                                padding: Theme.spacing.lg
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                color: Theme.colors.textPrimary
                                selectionColor: Theme.colors.accentSoft
                                selectedTextColor: Theme.colors.textPrimary
                                placeholderText: "Write narration for this section…"
                                font.family: Theme.type.family
                                font.pixelSize: Theme.type.body
                                background: Rectangle { color: "transparent" }
                                onTextChanged: {
                                    if (!root.syncingText && activeFocus && root.controller && root.controller.selectedSection.id)
                                        root.controller.updateSectionContent(root.controller.selectedSection.id, text)
                                }
                            }
                        }
                    }

                    AppTextField {
                        id: notesField
                        Layout.fillWidth: true
                        placeholderText: "Optional section note — e.g. use city image here"
                        onEditingFinished: if (root.controller && root.controller.selectedSection.id) root.controller.updateSectionNotes(root.controller.selectedSection.id, text)
                    }
                    ScriptStatsBar {
                        Layout.fillWidth: true
                        analysis: root.controller ? root.controller.analysis : ({})
                        languageName: root.controller ? (root.controller.script.languageName || "English") : "English"
                        saveState: root.controller ? root.controller.saveState : "Saved"
                    }
                    TTSPanel {
                        Layout.fillWidth: true
                        controller: root.ttsController
                        scriptController: root.controller
                        playbackController: root.playbackController
                        onToastRequested: function(message, variant) { root.toastRequested(message, variant) }
                    }
                }
            }
        }
    }

    FileDialog {
        id: importDialog
        title: "Import Script"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Text Files (*.txt)"]
        onAccepted: importChoiceDialog.open()
    }
    AppDialog {
        id: importChoiceDialog
        width: 450; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Import text script"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Add the TXT as a new section, or replace all current sections with one Imported Script section."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }
                SecondaryButton { text: "Add as Section"; onClicked: { importChoiceDialog.close(); root.controller.importText(importDialog.selectedFile, "add") } }
                AppButton { text: "Replace Script"; variant: "danger"; onClicked: { importChoiceDialog.close(); root.controller.importText(importDialog.selectedFile, "replace") } }
            }
        }
    }
    FileDialog {
        id: exportDialog
        title: "Export Script"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Text Files (*.txt)"]
        onAccepted: if (root.controller) root.controller.exportText(selectedFile)
    }

    AppDialog {
        id: addDialog
        width: 420; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            Text { text: "Add Section"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            AppTextField { id: addTitle; Layout.fillWidth: true; placeholderText: "Section name" }
            AppComboBox { id: addType; Layout.fillWidth: true; model: ["Body", "Custom"] }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Cancel"; onClicked: addDialog.close() }; AppButton { text: "Add"; onClicked: { if (root.controller && root.controller.addSection(addTitle.text, addType.currentIndex === 1 ? "custom" : "body")) addDialog.close() } } }
        }
    }

    AppDialog {
        id: deleteDialog
        width: 450; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Delete \"" + root.pendingDeleteTitle + "\"?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "This section contains text. This action cannot be undone through text undo."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Cancel"; onClicked: deleteDialog.close() }; AppButton { text: "Delete"; variant: "danger"; onClicked: { if (root.controller && root.controller.deleteSection(root.pendingDeleteId)) deleteDialog.close() } } }
        }
    }
}
