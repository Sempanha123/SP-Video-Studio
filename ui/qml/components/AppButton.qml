import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

Button {
    id: control
    property string variant: "primary"
    property string iconName: ""
    property bool compact: false

    implicitHeight: compact ? 34 : 38
    implicitWidth: Math.max(compact ? 88 : 104, contentRow.implicitWidth + Theme.spacing.xl * 2)
    leftPadding: Theme.spacing.lg
    rightPadding: Theme.spacing.lg

    font.family: Theme.type.family
    font.pixelSize: Theme.type.button
    font.weight: Theme.type.semibold

    contentItem: RowLayout {
        id: contentRow
        spacing: Theme.spacing.sm
        Icon {
            visible: control.iconName !== ""
            name: control.iconName
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
            opacity: control.enabled ? 0.95 : 0.45
        }
        Text {
            text: control.text
            font: control.font
            color: (control.variant === "primary" || control.variant === "danger") ? "#FFFFFF" : Theme.colors.textPrimary
            opacity: control.enabled ? 1 : 0.45
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Layout.fillWidth: true
        }
    }

    background: Rectangle {
        radius: Theme.radius.medium
        color: {
            if (!control.enabled) return Theme.colors.surfacePressed
            if (control.variant === "primary") {
                if (control.down) return Theme.colors.accentPressed
                if (control.hovered) return Theme.colors.accentHover
                return Theme.colors.accent
            }
            if (control.variant === "danger") {
                if (control.down) return Qt.darker(Theme.colors.danger, 1.12)
                if (control.hovered) return Qt.lighter(Theme.colors.danger, 1.08)
                return Theme.colors.danger
            }
            if (control.variant === "ghost") {
                if (control.down) return Theme.colors.surfacePressed
                if (control.hovered) return Theme.colors.surfaceHover
                return "transparent"
            }
            if (control.down) return Theme.colors.surfacePressed
            if (control.hovered) return Theme.colors.surfaceHover
            return Theme.colors.surface
        }
        border.color: control.variant === "primary" || control.variant === "danger" ? "transparent" : (control.activeFocus ? Theme.colors.focus : Theme.colors.border)
        border.width: control.activeFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
    }
}
