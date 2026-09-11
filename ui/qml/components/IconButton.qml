import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

Button {
    id: control
    property string iconName: "settings"
    property string tooltip: ""
    implicitWidth: 36
    implicitHeight: 36
    padding: 0

    contentItem: Icon {
        name: control.iconName
        width: 18
        height: 18
        anchors.centerIn: parent
        opacity: control.enabled ? 0.9 : 0.4
    }
    background: Rectangle {
        radius: Theme.radius.medium
        color: control.down ? Theme.colors.surfacePressed : (control.hovered ? Theme.colors.surfaceHover : "transparent")
        border.color: control.activeFocus ? Theme.colors.focus : "transparent"
        border.width: control.activeFocus ? 2 : 0
        Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
    }
    ToolTip.visible: hovered && tooltip !== ""
    ToolTip.text: tooltip
    ToolTip.delay: 450
}
