import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
ProgressBar {
    id: control
    implicitHeight: 6
    background: Rectangle { radius: 3; color: Theme.colors.surfacePressed }
    contentItem: Item { implicitHeight: 6; Rectangle { width: control.visualPosition * parent.width; height: parent.height; radius: 3; color: Theme.colors.accent; Behavior on width { NumberAnimation { duration: Theme.animation.normal } } } }
}
