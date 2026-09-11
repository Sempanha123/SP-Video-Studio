import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
TextField {
    id: control
    property string iconName: "search"
    signal clearRequested()
    implicitHeight: Theme.controlHeight
    leftPadding: 34; rightPadding: text.length ? 32 : Theme.spacing.md
    color: Theme.colors.textPrimary; placeholderTextColor: Theme.colors.textMuted
    font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall
    background: Rectangle { radius: Theme.radius.small; color: Theme.colors.surface; border.color: control.activeFocus ? Theme.colors.focus : Theme.colors.border; border.width: control.activeFocus ? 2 : 1 }
    Icon { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; width: 15; height: 15; name: control.iconName; opacity: 0.65 }
    ToolButton { visible: control.text.length > 0; anchors.right: parent.right; anchors.rightMargin: 3; anchors.verticalCenter: parent.verticalCenter; width: 28; height: 28; text: "×"; font.pixelSize: 16; onClicked: { control.clear(); control.clearRequested() }; background: Rectangle { color: parent.hovered ? Theme.colors.surfaceHover : "transparent"; radius: Theme.radius.small } }
}
