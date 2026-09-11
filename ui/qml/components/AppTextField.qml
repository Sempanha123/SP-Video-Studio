import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
TextField {
    id: control
    implicitHeight: Theme.controlHeight
    color: enabled ? Theme.colors.textPrimary : Theme.colors.textDisabled
    placeholderTextColor: Theme.colors.textMuted
    selectionColor: Theme.colors.accentSoft
    selectedTextColor: Theme.colors.textPrimary
    font.family: Theme.type.family; font.pixelSize: Theme.type.body
    leftPadding: Theme.spacing.md; rightPadding: Theme.spacing.md
    background: Rectangle { radius: Theme.radius.small; color: control.enabled ? Theme.colors.surface : Theme.colors.surfaceHover; border.color: control.activeFocus ? Theme.colors.focus : Theme.colors.border; border.width: control.activeFocus ? 2 : 1; Behavior on border.color { ColorAnimation { duration: Theme.animation.fast } } }
}
