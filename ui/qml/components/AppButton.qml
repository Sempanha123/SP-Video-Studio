import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Button {
    id: control
    property string variant: "primary"
    property string iconName: ""
    property bool compact: false
    property string tooltip: ""
    property string shortcutHint: ""
    property string accessibleName: text.length > 0 ? text : (tooltip.length > 0 ? tooltip : "Action")
    property string size: compact ? "small" : "normal"
    implicitHeight: size === "large" ? Theme.controlHeightLarge : (size === "small" ? Theme.controlHeightSmall : Theme.controlHeight)
    implicitWidth: Math.max(size === "small" ? 76 : 92, contentRow.implicitWidth + Theme.spacing.lg * 2)
    leftPadding: Theme.spacing.md; rightPadding: Theme.spacing.md
    font.family: Theme.type.family; font.pixelSize: Theme.type.button; font.weight: Theme.type.semibold
    Accessible.name: accessibleName
    Accessible.description: tooltip
    Accessible.role: Accessible.Button
    ToolTip.visible: hovered && (tooltip.length > 0 || shortcutHint.length > 0)
    ToolTip.text: tooltip + (tooltip.length > 0 && shortcutHint.length > 0 ? "  ·  " : "") + shortcutHint
    ToolTip.delay: Theme.tooltipDelay
    contentItem: RowLayout {
        id: contentRow; spacing: Theme.spacing.sm
        Icon { visible: control.iconName !== ""; name: control.iconName; Layout.preferredWidth: 16; Layout.preferredHeight: 16; opacity: control.enabled ? 0.9 : 0.4 }
        Text { text: control.text; font: control.font; color: control.enabled ? ((control.variant === "primary") ? Theme.colors.onAccent : (control.variant === "danger" ? Theme.colors.danger : Theme.colors.textPrimary)) : Theme.colors.textDisabled; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; Layout.fillWidth: true; elide: Text.ElideRight }
    }
    background: Rectangle {
        radius: Theme.radius.small
        color: {
            if (!control.enabled) return Theme.colors.surfaceHover
            if (control.variant === "primary") return control.down ? Theme.colors.accentPressed : (control.hovered ? Theme.colors.accentHover : Theme.colors.accent)
            if (control.variant === "danger") return control.down || control.hovered ? Theme.colors.dangerSoft : "transparent"
            if (control.variant === "quiet" || control.variant === "ghost") return control.down ? Theme.colors.surfacePressed : (control.hovered ? Theme.colors.surfaceHover : "transparent")
            return control.down ? Theme.colors.surfacePressed : (control.hovered ? Theme.colors.surfaceHover : Theme.colors.surface)
        }
        border.color: control.visualFocus ? Theme.colors.focus : ((control.variant === "secondary" || control.variant === "default") ? Theme.colors.border : "transparent")
        border.width: control.visualFocus ? Theme.focusWidth : ((control.variant === "secondary" || control.variant === "default") ? 1 : 0)
        Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
        Behavior on border.color { ColorAnimation { duration: Theme.animation.fast } }
    }
}
