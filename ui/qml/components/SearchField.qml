import QtQuick 2.15
import QtQuick.Controls 2.15
import SPVideoStudio.Commands 1.0
import "../theme"
TextField {
    id: control
    property string iconName: "search"
    property string accessibleName: placeholderText.length > 0 ? placeholderText : "Search"
    signal clearRequested()
    implicitHeight: Theme.controlHeight
    leftPadding: 34; rightPadding: text.length ? 32 : Theme.spacing.md
    color: Theme.colors.textPrimary; placeholderTextColor: Theme.colors.textMuted
    font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall
    Accessible.name: accessibleName
    Accessible.role: Accessible.EditableText
    onActiveFocusChanged: Commands.setTextEditing(activeFocus)
    Keys.onEscapePressed: function(event) { if (control.text.length > 0) { control.clear(); control.clearRequested(); event.accepted = true } }
    background: Rectangle { radius: Theme.radius.small; color: Theme.colors.surface; border.color: control.activeFocus ? Theme.colors.focus : Theme.colors.border; border.width: control.activeFocus ? Theme.focusWidth : 1 }
    Icon { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; width: 15; height: 15; name: control.iconName; opacity: 0.72 }
    ToolButton {
        visible: control.text.length > 0; anchors.right: parent.right; anchors.rightMargin: 3; anchors.verticalCenter: parent.verticalCenter; width: 28; height: 28; text: "×"; font.pixelSize: 16
        Accessible.name: "Clear search"; Accessible.role: Accessible.Button
        ToolTip.visible: hovered; ToolTip.text: "Clear search"; ToolTip.delay: Theme.tooltipDelay
        onClicked: { control.clear(); control.clearRequested(); control.forceActiveFocus(Qt.TabFocusReason) }
        background: Rectangle { color: parent.hovered ? Theme.colors.surfaceHover : "transparent"; radius: Theme.radius.small }
    }
}
