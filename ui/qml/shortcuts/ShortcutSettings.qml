import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

AppDialog {
    id: root
    width: Math.min(900, parent ? parent.width - 48 : 900)
    height: Math.min(680, parent ? parent.height - 64 : 680)
    header: null
    footer: null
    modal: true
    property var rows: []
    signal toastRequested(string message, string variant)

    function refresh() { rows = Shortcuts.search(searchField.text) }
    onOpened: { Commands.setModalOpen(true); refresh(); searchField.forceActiveFocus() }
    onClosed: Commands.setModalOpen(false)

    Connections {
        target: Shortcuts
        function onChanged() { root.refresh() }
        function onConflictDetected(commandId, sequence, message) {
            conflictDialog.sequence = sequence
            conflictDialog.message = message
            conflictDialog.open()
        }
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
    }

    contentItem: ColumnLayout {
        spacing: Theme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Keyboard Shortcuts"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
                Text { text: "Customize optional shortcuts. Mouse workflows remain available."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            }
            IconButton { iconName: "close"; tooltip: "Close"; onClicked: root.close() }
        }
        RowLayout {
            Layout.fillWidth: true
            AppTextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Search command, category or shortcut…"
                onTextChanged: root.refresh()
            }
            SecondaryButton { text: "Reset All"; onClicked: resetAllDialog.open() }
        }
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: "Command"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold }
            Text { Layout.preferredWidth: 150; text: "Shortcut"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold }
            Text { Layout.preferredWidth: 140; text: "Category"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold }
            Item { Layout.preferredWidth: 36 }
        }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            reuseItems: true
            model: root.rows
            delegate: Rectangle {
                required property var modelData
                width: list.width
                height: 54
                color: index % 2 ? Theme.colors.surfaceRaised : Theme.colors.surface
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacing.sm
                    anchors.rightMargin: Theme.spacing.sm
                    spacing: Theme.spacing.sm
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { Layout.fillWidth: true; text: modelData.name; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                        Text { Layout.fillWidth: true; text: modelData.description; elide: Text.ElideRight; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    }
                    SecondaryButton {
                        Layout.preferredWidth: 150
                        text: modelData.shortcut || "Unassigned"
                        compact: true
                        onClicked: recorder.begin(modelData.id, modelData.name)
                    }
                    Text { Layout.preferredWidth: 140; text: modelData.category; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    IconButton { iconName: "refresh"; tooltip: "Reset to Default"; onClicked: Shortcuts.resetCommand(modelData.id) }
                }
            }
            ScrollBar.vertical: ScrollBar {}
        }
    }

    ShortcutRecorder {
        id: recorder
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        onAcceptedShortcut: function(commandId, sequence) { Shortcuts.setShortcut(commandId, sequence) }
    }
    ShortcutConflictDialog {
        id: conflictDialog
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
    }
    AppDialog {
        id: resetAllDialog
        width: 440
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null
        footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Reset all keyboard shortcuts?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading }
            Text { Layout.fillWidth: true; text: "Your custom assignments will be removed and built-in defaults restored."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: resetAllDialog.close() }
                AppButton { text: "Reset"; onClicked: { Shortcuts.resetAll(); resetAllDialog.close() } }
            }
        }
    }
}
