import QtQuick 2.15
import "../theme"
Rectangle {
    id: card
    property bool interactive: false
    property bool selected: false
    property bool elevated: false
    signal clicked()
    radius: Theme.radius.card
    color: selected ? Theme.colors.surfaceSelected : (mouse.containsMouse && interactive ? Theme.colors.surfaceHover : (elevated ? Theme.colors.surfaceRaised : Theme.colors.surface))
    border.width: selected || activeFocus ? 1 : 1
    border.color: selected || activeFocus ? Theme.colors.accent : Theme.colors.border
    focus: interactive
    scale: interactive && mouse.containsMouse && !Theme.reducedMotion ? 1.003 : 1.0
    HoverHandler { id: hover }
    MouseArea { id: mouse; anchors.fill: parent; enabled: card.interactive; hoverEnabled: true; cursorShape: card.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: card.clicked() }
    Keys.onSpacePressed: if (interactive) clicked()
    Keys.onReturnPressed: if (interactive) clicked()
    Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animation.fast } }
    Behavior on scale { NumberAnimation { duration: Theme.animation.fast } }
}
