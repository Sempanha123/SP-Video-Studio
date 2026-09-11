import QtQuick 2.15
import "../theme"
Item {
    id: root
    property real pixelsPerSecond: 80
    property int durationMs: 0
    height: 34
    width: Math.max(1,durationMs/1000*pixelsPerSecond)
    property real intervalSeconds: pixelsPerSecond >= 220 ? .5 : pixelsPerSecond >= 100 ? 1 : pixelsPerSecond >= 45 ? 5 : 10
    Repeater {
        model: Math.ceil(root.durationMs/1000/root.intervalSeconds)+1
        delegate: Item {
            required property int index
            x: index*root.intervalSeconds*root.pixelsPerSecond; width: 1; height: root.height
            Rectangle { width:1; height: index%5===0 ? 14 : 8; anchors.bottom: parent.bottom; color: Theme.colors.borderStrong }
            Text { x:4; y:2; visible: root.pixelsPerSecond*root.intervalSeconds >= 34; text: { var sec=index*root.intervalSeconds; var m=Math.floor(sec/60); return m+":"+String(Math.floor(sec%60)).padStart(2,"0") } color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:10 }
        }
    }
}
