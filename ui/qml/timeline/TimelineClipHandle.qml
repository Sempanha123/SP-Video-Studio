import QtQuick 2.15
import "../theme"
Rectangle {
    width: 6; radius: 3; color: Theme.colors.focus; opacity: handleArea.containsMouse || parent.selected ? .9 : .45
    property bool selected: false
    signal dragged(real deltaX)
    MouseArea { id: handleArea; anchors.fill: parent; anchors.margins: -5; hoverEnabled: true; cursorShape: Qt.SizeHorCursor; property real pressX: 0
        onPressed: pressX = mouse.x
        onReleased: parent.dragged(mouse.x - pressX)
    }
}
