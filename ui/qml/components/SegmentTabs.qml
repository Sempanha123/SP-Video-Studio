import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
RowLayout {
    id: root
    property var items: []
    property int currentIndex: 0
    signal activated(int index)
    spacing: 2
    Repeater { model: root.items; delegate: Button { required property int index; required property var modelData; text: String(modelData); implicitHeight: 30; padding: 8; font.family: Theme.type.family; font.pixelSize: Theme.type.small; contentItem: Text { text: parent.text; color: index === root.currentIndex ? Theme.colors.textPrimary : Theme.colors.textSecondary; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }; background: Rectangle { radius: Theme.radius.small; color: index === root.currentIndex ? Theme.colors.surfaceSelected : (parent.hovered ? Theme.colors.surfaceHover : "transparent"); border.width: index === root.currentIndex ? 1 : 0; border.color: Theme.colors.borderStrong }; onClicked: root.activated(index) } }
}
