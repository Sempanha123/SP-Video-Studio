import QtQuick 2.15
import QtQuick.Controls 2.15
import SPVideoStudio.Commands 1.0

Item {
    id: root
    required property var window
    anchors.fill: parent
    visible: false

    function isTextEditor(item) {
        if (!item) return false
        // TextField/TextArea/TextInput/TextEdit all expose text + cursorPosition.
        // This avoids depending on concrete control classes and protects custom text fields.
        return ("text" in item) && ("cursorPosition" in item)
    }

    function syncFocus() {
        Commands.setWindowActive(window.active)
        Commands.setTextEditing(isTextEditor(window.activeFocusItem))
    }

    Connections {
        target: window
        function onActiveFocusItemChanged() { root.syncFocus() }
        function onActiveChanged() { root.syncFocus() }
    }

    Repeater {
        model: Commands.activeBindings
        delegate: Shortcut {
            required property var modelData
            sequence: modelData.sequence
            context: Qt.ApplicationShortcut
            enabled: Boolean(modelData.enabled) && root.window.active
            onActivated: Commands.dispatch(modelData.sequence)
        }
    }

    Component.onCompleted: syncFocus()
}
