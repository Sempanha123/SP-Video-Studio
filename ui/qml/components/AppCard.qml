import QtQuick 2.15
import "../theme"

Rectangle {
    id: card
    property bool interactive: false
    property bool selected: false
    signal clicked()
    radius: Theme.radius.large
    color: selected ? Theme.colors.accentSoft : (mouse.containsMouse && interactive ? Theme.colors.surfaceHover : Theme.colors.surface)
    border.width: selected || activeFocus ? 2 : 1
    border.color: selected || activeFocus ? Theme.colors.accent : Theme.colors.border
    focus: interactive

    HoverHandler { id: hover }
    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: card.interactive
        hoverEnabled: true
        cursorShape: card.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: card.clicked()
    }
    Keys.onSpacePressed: if (interactive) clicked()
    Keys.onReturnPressed: if (interactive) clicked()
    Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animation.fast } }
}
