import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

Item {
    id: root
    property string text: "Home"
    property string iconName: "home"
    property bool selected: false
    signal clicked()
    implicitHeight: 40
    focus: true

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius.medium
        color: root.selected ? Theme.colors.accentSoft : (mouse.containsMouse ? Theme.colors.surfaceHover : "transparent")
        border.color: root.activeFocus ? Theme.colors.focus : "transparent"
        border.width: root.activeFocus ? 2 : 0
        Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
    }
    Rectangle {
        visible: root.selected
        width: 3
        height: 18
        radius: 2
        color: Theme.colors.accent
        anchors.left: parent.left
        anchors.leftMargin: 2
        anchors.verticalCenter: parent.verticalCenter
    }
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing.md
        anchors.rightMargin: Theme.spacing.md
        spacing: Theme.spacing.md
        Icon { name: root.iconName; Layout.preferredWidth: 18; Layout.preferredHeight: 18 }
        Text {
            text: root.text
            color: root.selected ? Theme.colors.textPrimary : Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.bodySmall
            font.weight: root.selected ? Theme.type.semibold : Theme.type.regular
            Layout.fillWidth: true
            verticalAlignment: Text.AlignVCenter
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    Keys.onSpacePressed: clicked()
    Keys.onReturnPressed: clicked()
}
