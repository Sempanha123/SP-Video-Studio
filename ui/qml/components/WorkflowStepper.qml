import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item {
    id: root
    property var steps: []
    property int currentIndex: 0
    property var attentionIndexes: []
    signal stepRequested(int index)
    implicitHeight: 36
    RowLayout {
        anchors.fill: parent; spacing: 3
        Repeater {
            model: root.steps
            delegate: Button {
                required property int index; required property var modelData
                Layout.fillWidth: true; implicitHeight: 32
                text: String(modelData)
                font.family: Theme.type.family; font.pixelSize: Theme.type.small; font.weight: index === root.currentIndex ? Theme.type.semibold : Theme.type.medium
                contentItem: Text { text: parent.text; color: index === root.currentIndex ? Theme.colors.accent : (index < root.currentIndex ? Theme.colors.success : Theme.colors.textSecondary); font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                background: Rectangle { radius: Theme.radius.small; color: index === root.currentIndex ? Theme.colors.accentSoft : (parent.hovered ? Theme.colors.surfaceHover : "transparent"); border.width: root.attentionIndexes.indexOf(index) >= 0 ? 1 : 0; border.color: Theme.colors.warning }
                onClicked: root.stepRequested(index)
            }
        }
    }
}
