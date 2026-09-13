import QtQuick 2.15
import QtQuick.Controls 2.15
import SPVideoStudio.Commands 1.0
import "../theme"
TextField {
    id: control
    property string tooltip: ""
    property string shortcutHint: ""
    property string accessibleName: placeholderText.length > 0 ? placeholderText : "Text field"
    implicitHeight: Theme.controlHeight
    color: enabled ? Theme.colors.textPrimary : Theme.colors.textDisabled
    placeholderTextColor: Theme.colors.textMuted
    selectionColor: Theme.colors.accentSoft
    selectedTextColor: Theme.colors.textPrimary
    font.family: Theme.type.family; font.pixelSize: Theme.type.body
    leftPadding: Theme.spacing.md; rightPadding: Theme.spacing.md
    Accessible.name: accessibleName
    Accessible.description: tooltip
    Accessible.role: Accessible.EditableText
    onActiveFocusChanged: Commands.setTextEditing(activeFocus)
    ToolTip.visible: hovered && (tooltip.length>0 || shortcutHint.length>0)
    ToolTip.text: tooltip + (tooltip.length>0 && shortcutHint.length>0 ? "  ·  " : "") + shortcutHint
    ToolTip.delay: Theme.tooltipDelay
    background: Rectangle { radius: Theme.radius.small; color: control.enabled ? Theme.colors.surface : Theme.colors.surfaceHover; border.color: control.visualFocus ? Theme.colors.focus : Theme.colors.border; border.width: control.visualFocus ? Theme.focusWidth : 1; Behavior on border.color { ColorAnimation { duration: Theme.animation.fast } } }
}
