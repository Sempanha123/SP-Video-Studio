import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property string cueId: ""
    property int startMs: 0
    property int endMs: 0
    property string timeText: ""
    property string cueText: ""
    property string secondaryText: ""
    property bool edited: false
    property bool activeCue: false
    property bool sourceChanged: false
    property bool sourceMissing: false
    property string warning: ""
    signal selectRequested(string cueId)
    signal mergeRequested(string cueId)

    border.color: activeCue ? Theme.colors.accent : Theme.colors.border
    accessibleName: "Subtitle " + root.timeText + ". " + root.cueText + (root.edited ? ". Edited" : "") + (root.sourceChanged ? ". Source changed" : "") + (root.sourceMissing ? ". Source missing" : "")
    Accessible.role: Accessible.ListItem
    Accessible.selected: root.activeCue
    implicitHeight: content.implicitHeight + Theme.spacing.md * 2

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.sm

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: root.timeText
                color: Theme.colors.textSecondary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.caption
                font.weight: Theme.type.semibold
            }
            Text { visible: root.edited; text: "Edited"; color: Theme.colors.accent; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { visible: root.sourceChanged; text: "Source Changed"; color: Theme.colors.warning; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { visible: root.sourceMissing; text: "Source Missing"; color: Theme.colors.warning; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Play"; compact: true; accessibleName: "Play subtitle cue"; tooltip: "Play Subtitle Cue"; onClicked: { root.selectRequested(root.cueId); if (root.controller) root.controller.playSelected(true) } }
        }

        TextArea {
            id: primary
            Layout.fillWidth: true
            text: root.cueText
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            color: Theme.colors.textPrimary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.body
            lineHeightMode: TextEdit.ProportionalHeight
            lineHeight: Theme.type.multilingualLineHeight
            Accessible.name: "Subtitle text"
            Accessible.role: Accessible.EditableText
            background: Rectangle { radius: Theme.radius.small; color: Theme.colors.surfaceAlt; border.color: primary.activeFocus ? Theme.colors.accent : Theme.colors.border }
            onActiveFocusChanged: { Commands.setTextEditing(activeFocus); if (!activeFocus && root.controller) root.controller.queueText(root.cueId, text, secondary.text) }
        }

        TextArea {
            id: secondary
            Layout.fillWidth: true
            visible: root.secondaryText.length > 0
            text: root.secondaryText
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.bodySmall
            lineHeightMode: TextEdit.ProportionalHeight
            lineHeight: Theme.type.multilingualLineHeight
            Accessible.name: "Secondary subtitle text"
            Accessible.role: Accessible.EditableText
            background: Rectangle { radius: Theme.radius.small; color: Theme.colors.surfaceAlt; border.color: secondary.activeFocus ? Theme.colors.accent : Theme.colors.border }
            onActiveFocusChanged: { Commands.setTextEditing(activeFocus); if (!activeFocus && root.controller) root.controller.queueText(root.cueId, primary.text, text) }
        }

        Text {
            Layout.fillWidth: true
            visible: root.warning.length > 0
            text: root.warning
            color: Theme.colors.warning
            wrapMode: Text.WordWrap
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
        }
    }

    MouseArea {
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 32
        acceptedButtons: Qt.LeftButton
        onClicked: root.selectRequested(root.cueId)
    }
}
