import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
Rectangle {
    id: root
    property var clipData: ({})
    property real pixelsPerSecond: 80
    property bool selected: false
    property bool trackLocked: false
    property color clipColor: Theme.colors.accentSoft
    property string trackName: "Timeline track"
    property string trackType: ""
    signal activated(string clipId, int modifiers)
    signal moveDropped(var clipData, real xPosition)
    signal trimLeftDropped(var clipData, real deltaPixels)
    signal trimRightDropped(var clipData, real deltaPixels)
    signal contextRequested(var clipData, real globalX, real globalY)
    function secondsText(ms) { return (Number(ms||0)/1000).toFixed(1) + " seconds" }
    x: Number(clipData.startMs || 0) / 1000 * pixelsPerSecond
    width: Math.max(8, Number(clipData.durationMs || 1) / 1000 * pixelsPerSecond)
    height: parent ? parent.height - 10 : 48
    y: 5
    radius: Theme.radius.small
    color: selected ? Theme.colors.accentSoft : clipColor
    border.color: selected ? Theme.colors.focus : Theme.colors.borderStrong
    border.width: selected ? Theme.focusWidth : 1
    opacity: clipData.enabled === false ? .45 : 1
    clip: true
    activeFocusOnTab: false
    Accessible.role: Accessible.ListItem
    Accessible.selected: selected
    Accessible.name: String(clipData.label || clipData.sourceType || "Clip") + ". " + trackName + ". Starts at " + secondsText(clipData.startMs) + ". Duration " + secondsText(clipData.durationMs) + (clipData.metadata && clipData.metadata.missing ? ". Missing media" : "")

    Text { anchors.left: parent.left; anchors.leftMargin: 8; anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; text: root.width > 70 ? (clipData.label || clipData.sourceType || "Clip") : ""; color: Theme.colors.textPrimary; elide: Text.ElideRight; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
    Text { anchors.right: parent.right; anchors.rightMargin: 6; anchors.bottom: parent.bottom; anchors.bottomMargin: 3; visible: root.width > 110; text: ((Number(clipData.durationMs || 0)/1000).toFixed(1)) + "s"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.timeline }
    Text { anchors.left: parent.left; anchors.leftMargin: 5; anchors.top: parent.top; anchors.topMargin: 2; visible: clipData.metadata && clipData.metadata.missing; text: "⚠ Missing"; color: Theme.colors.warning; font.family: Theme.type.family; font.pixelSize: Theme.type.timeline }
    Text { anchors.right: parent.right; anchors.rightMargin: 5; anchors.top: parent.top; anchors.topMargin: 2; visible: clipData.metadata && clipData.metadata.transitionType && clipData.metadata.transitionType !== "cut"; text: String(clipData.metadata.transitionType) + " " + String(clipData.metadata.transitionDurationMs || 0) + "ms"; color: Theme.colors.info; font.family: Theme.type.family; font.pixelSize: Theme.type.timeline }

    MouseArea {
        id: dragArea; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton | Qt.RightButton; enabled: !root.trackLocked
        drag.target: root; drag.axis: Drag.XAxis; drag.minimumX: 0
        onPressed: { root.activated(String(root.clipData.id || ""), mouse.modifiers); if (mouse.button === Qt.RightButton) { var p=mapToItem(null,mouse.x,mouse.y); root.contextRequested(root.clipData,p.x,p.y) } }
        onReleased: if (mouse.button === Qt.LeftButton && drag.active) root.moveDropped(root.clipData, root.x)
    }
    TimelineClipHandle { anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; selected: root.selected; visible: root.selected && !root.trackLocked; onDragged: function(dx) { root.trimLeftDropped(root.clipData, dx) } }
    TimelineClipHandle { anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; selected: root.selected; visible: root.selected && !root.trackLocked; onDragged: function(dx) { root.trimRightDropped(root.clipData, dx) } }
}
