import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
import "../accessibility"
Rectangle {
    id: card
    property bool interactive: false
    property bool selected: false
    property bool elevated: false
    property string accessibleName: ""
    signal clicked()
    radius: Theme.radius.card
    color: selected ? Theme.colors.surfaceSelected : (mouse.containsMouse && interactive ? Theme.colors.surfaceHover : (elevated ? Theme.colors.surfaceRaised : Theme.colors.surface))
    border.width: 1
    border.color: selected ? Theme.colors.accent : Theme.colors.border
    focus: interactive
    activeFocusOnTab: interactive
    Accessible.name: accessibleName
    Accessible.role: interactive ? Accessible.Button : Accessible.Pane
    scale: interactive && mouse.containsMouse && !Theme.reducedMotion ? 1.003 : 1.0
    HoverHandler { id: hover }
    MouseArea { id: mouse; anchors.fill: parent; enabled: card.interactive; hoverEnabled: true; cursorShape: card.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: card.clicked() }
    Keys.onSpacePressed: function(event) { if (interactive) { clicked(); event.accepted = true } }
    Keys.onReturnPressed: function(event) { if (interactive) { clicked(); event.accepted = true } }
    FocusRing { focused: card.activeFocus }
    Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animation.fast } }
    Behavior on scale { NumberAnimation { duration: Theme.animation.fast } }
}
