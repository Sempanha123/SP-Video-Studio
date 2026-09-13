import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
Switch {
    id: control
    property string accessibleName: text.length > 0 ? text : "Toggle"
    Accessible.name: accessibleName
    Accessible.role: Accessible.CheckBox
    Accessible.checked: checked
    indicator: Rectangle {
        implicitWidth: 40; implicitHeight: 22; x: control.leftPadding; y: parent.height / 2 - height / 2; radius: height / 2
        color: control.checked ? Theme.colors.accent : Theme.colors.borderStrong
        border.color: control.visualFocus ? Theme.colors.focus : "transparent"
        border.width: control.visualFocus ? Theme.focusWidth : 0
        Rectangle { x: control.checked ? parent.width - width - 3 : 3; y: 3; width: 16; height: 16; radius: 8; color: "white"; Behavior on x { NumberAnimation { duration: Theme.animation.normal; easing.type: Easing.OutCubic } } }
        Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
    }
}
