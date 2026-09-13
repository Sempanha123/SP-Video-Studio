import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

RowLayout {
    property string title: "Section"
    property string actionText: ""
    signal actionClicked()
    spacing: Theme.spacing.md
    Text {
        text: parent.title
        Accessible.role: Accessible.Heading
        Accessible.name: text
        color: Theme.colors.textPrimary
        font.family: Theme.type.family
        font.pixelSize: Theme.type.heading
        font.weight: Theme.type.semibold
        Layout.fillWidth: true
    }
    Text {
        visible: parent.actionText !== ""
        text: parent.actionText
        activeFocusOnTab: visible
        Accessible.role: Accessible.Button
        Accessible.name: text
        color: Theme.colors.accent
        font.family: Theme.type.family
        font.pixelSize: Theme.type.caption
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: parent.parent.actionClicked() }
        Keys.onReturnPressed: function(event) { parent.parent.actionClicked(); event.accepted = true }
        Keys.onSpacePressed: function(event) { parent.parent.actionClicked(); event.accepted = true }
    }
}
