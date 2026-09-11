import QtQuick 2.15
import "../theme"
Item {
    id: root
    property int playheadMs: 0
    property real pixelsPerSecond: 80
    signal seekRequested(int positionMs)
    x: playheadMs/1000*pixelsPerSecond - 1
    width: 12
    Rectangle { x:5; width:2; height:parent.height; color:Theme.colors.danger }
    Rectangle { x:1; y:0; width:10; height:10; radius:2; color:Theme.colors.danger; rotation:45 }
    MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.SizeHorCursor; drag.target: root; drag.axis: Drag.XAxis; drag.minimumX: -1; onReleased: root.seekRequested(Math.max(0,Math.round((root.x+1)/root.pixelsPerSecond*1000))) }
}
