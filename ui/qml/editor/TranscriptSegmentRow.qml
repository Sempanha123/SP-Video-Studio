import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property string segmentId: ""
    property int startMs: 0
    property int endMs: 0
    property string startText: "00:00.000"
    property string endText: "00:00.000"
    property string segmentText: ""
    property string originalText: ""
    property bool edited: false
    signal textEdited(string segmentId, string text)
    signal resetRequested(string segmentId)
    signal playRequested(string segmentId, int startMs)

    implicitHeight: Math.max(98, editor.implicitHeight + Theme.spacing.lg * 2)

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.md

        ColumnLayout {
            Layout.preferredWidth: 100
            spacing: Theme.spacing.xs
            Text { text: root.startText; color: Theme.colors.textPrimary; font.family: Theme.type.monoFamily; font.pixelSize: Theme.type.caption }
            Text { text: "to " + root.endText; color: Theme.colors.textMuted; font.family: Theme.type.monoFamily; font.pixelSize: Theme.type.caption }
            SecondaryButton { text: "Play"; compact: true; onClicked: root.playRequested(root.segmentId, root.startMs) }
        }

        TextArea {
            id: editor
            Layout.fillWidth: true
            Layout.minimumHeight: 72
            text: root.segmentText
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            color: Theme.colors.textPrimary
            selectionColor: Theme.colors.accentSoft
            selectedTextColor: Theme.colors.textPrimary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.body
            background: Rectangle {
                radius: Theme.radius.medium
                color: editor.activeFocus ? Theme.colors.surfaceHover : Theme.colors.surface
                border.color: editor.activeFocus ? Theme.colors.focus : Theme.colors.border
                border.width: editor.activeFocus ? 2 : 1
            }
            onTextChanged: {
                if (activeFocus && text !== root.segmentText)
                    root.textEdited(root.segmentId, text)
            }
        }

        ColumnLayout {
            Layout.preferredWidth: 170
            spacing: Theme.spacing.xs
            StatusBadge { visible: root.edited; text: "Edited"; status: "warning" }
            SecondaryButton { visible: root.edited; text: "Reset to Generated Text"; compact: true; onClicked: root.resetRequested(root.segmentId) }
        }
    }
}
