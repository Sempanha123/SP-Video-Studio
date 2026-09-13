import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
ComboBox {
    id: control
    property string accessibleName: "Selection"
    implicitHeight: Math.max(38, Theme.controlHeight)
    font.family: Theme.type.family
    font.pixelSize: Theme.type.body
    leftPadding: Theme.spacing.md
    rightPadding: Theme.spacing.xl
    Accessible.name: accessibleName
    Accessible.role: Accessible.ComboBox
    contentItem: Text { text: control.displayText; color: Theme.colors.textPrimary; font: control.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
    background: Rectangle { radius: Theme.radius.medium; color: control.down ? Theme.colors.surfacePressed : (control.hovered ? Theme.colors.surfaceHover : Theme.colors.surface); border.color: control.visualFocus ? Theme.colors.focus : Theme.colors.border; border.width: control.visualFocus ? Theme.focusWidth : 1 }
}
