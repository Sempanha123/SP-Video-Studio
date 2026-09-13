import QtQuick 2.15
import "../theme"
Rectangle {
    id: ring
    property bool focused: false
    anchors.fill: parent
    anchors.margins: -2
    radius: Math.max(Theme.radius.small, parent && parent.radius !== undefined ? parent.radius + 2 : Theme.radius.small)
    color: "transparent"
    border.color: Theme.colors.focus
    border.width: Theme.focusWidth
    visible: focused
    opacity: Theme.strongerFocus ? 1.0 : 0.82
    z: 999
}
