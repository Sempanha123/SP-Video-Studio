import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppDialog {
    id: root
    width: 430
    header: null
    footer: null
    modal: true
    property string commandId: ""
    property string commandName: ""
    property string recordedSequence: ""
    signal acceptedShortcut(string commandId, string sequence)

    function modifierText(modifiers) {
        var p = []
        if (modifiers & Qt.ControlModifier) p.push("Ctrl")
        if (modifiers & Qt.AltModifier) p.push("Alt")
        if (modifiers & Qt.ShiftModifier) p.push("Shift")
        if (modifiers & Qt.MetaModifier) p.push("Meta")
        return p
    }

    function keyText(key, text) {
        if (key === Qt.Key_Delete) return "Delete"
        if (key === Qt.Key_Escape) return "Escape"
        if (key === Qt.Key_Space) return "Space"
        if (key === Qt.Key_Return || key === Qt.Key_Enter) return "Enter"
        if (key === Qt.Key_Left) return "Left"
        if (key === Qt.Key_Right) return "Right"
        if (key === Qt.Key_Up) return "Up"
        if (key === Qt.Key_Down) return "Down"
        if (key === Qt.Key_Home) return "Home"
        if (key === Qt.Key_End) return "End"
        if (key >= Qt.Key_F1 && key <= Qt.Key_F12) return "F" + (key - Qt.Key_F1 + 1)
        if (text && text.length === 1) return text.toUpperCase()
        return ""
    }

    function begin(id, name) {
        commandId = id
        commandName = name
        recordedSequence = ""
        open()
        capture.forceActiveFocus()
    }

    contentItem: ColumnLayout {
        spacing: Theme.spacing.lg
        Text {
            text: "Record shortcut"
            color: Theme.colors.textPrimary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.heading
            font.weight: Theme.type.semibold
        }
        Text {
            Layout.fillWidth: true
            text: root.commandName
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.body
            wrapMode: Text.WordWrap
        }
        Rectangle {
            id: capture
            Layout.fillWidth: true
            Layout.preferredHeight: 86
            radius: Theme.radius.control
            color: Theme.colors.surfaceRaised
            border.color: activeFocus ? Theme.colors.accent : Theme.colors.borderStrong
            focus: true
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Control || event.key === Qt.Key_Shift ||
                    event.key === Qt.Key_Alt || event.key === Qt.Key_Meta) {
                    event.accepted = true
                    return
                }
                var parts = root.modifierText(event.modifiers)
                var key = root.keyText(event.key, event.text)
                if (key.length > 0) {
                    parts.push(key)
                    root.recordedSequence = parts.join("+")
                }
                event.accepted = true
            }
            Text {
                anchors.centerIn: parent
                text: root.recordedSequence.length ? root.recordedSequence : "Press shortcut…"
                color: root.recordedSequence.length ? Theme.colors.textPrimary : Theme.colors.textMuted
                font.family: Theme.type.family
                font.pixelSize: Theme.type.title
            }
        }
        Text {
            text: "Single key sequences only. Complex multi-key chords are intentionally not used."
            color: Theme.colors.textMuted
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Cancel"; onClicked: root.close() }
            AppButton {
                text: "Use Shortcut"
                enabled: root.recordedSequence.length > 0
                onClicked: {
                    root.acceptedShortcut(root.commandId, root.recordedSequence)
                    root.close()
                }
            }
        }
    }
}
