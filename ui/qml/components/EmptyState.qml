import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

ColumnLayout {
    id: root
    property string iconName: "folder"
    property string title: "Nothing here yet"
    property string description: ""
    property string actionText: ""
    signal actionClicked()
    spacing: Theme.spacing.md
    Layout.alignment: Qt.AlignHCenter

    Rectangle {
        Layout.alignment: Qt.AlignHCenter
        width: 52; height: 52; radius: 16
        color: Theme.colors.surfaceHover
        Icon { anchors.centerIn: parent; width: 24; height: 24; name: root.iconName }
    }
    Text {
        Layout.alignment: Qt.AlignHCenter
        text: root.title
        color: Theme.colors.textPrimary
        font.family: Theme.type.family
        font.pixelSize: Theme.type.title
        font.weight: Theme.type.semibold
    }
    Text {
        Layout.alignment: Qt.AlignHCenter
        Layout.maximumWidth: 460
        text: root.description
        color: Theme.colors.textSecondary
        font.family: Theme.type.family
        font.pixelSize: Theme.type.body
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }
    AppButton {
        visible: root.actionText !== ""
        Layout.alignment: Qt.AlignHCenter
        text: root.actionText
        onClicked: root.actionClicked()
    }
}
