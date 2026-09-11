import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

TextField {
    id: control
    implicitHeight: 38
    color: Theme.colors.textPrimary
    placeholderTextColor: Theme.colors.textMuted
    selectionColor: Theme.colors.accent
    selectedTextColor: "white"
    font.family: Theme.type.family
    font.pixelSize: Theme.type.body
    leftPadding: Theme.spacing.md
    rightPadding: Theme.spacing.md
    background: Rectangle {
        radius: Theme.radius.medium
        color: Theme.colors.surface
        border.color: control.activeFocus ? Theme.colors.focus : Theme.colors.border
        border.width: control.activeFocus ? 2 : 1
    }
}
