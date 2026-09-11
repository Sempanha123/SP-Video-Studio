import QtQuick 2.15
import "../theme"

Item {
    id: root
    property var track: ({})
    property var controller
    property real pixelsPerSecond: 80
    property real timelineWidth: 1000
    width: timelineWidth
    height: Number(track.height || 64)

    Rectangle { anchors.fill: parent; color: index % 2 === 0 ? Theme.colors.surface : Theme.colors.surfaceRaised; border.color: Theme.colors.border; border.width: 1 }
    function accent(kind) {
        if (kind === "video") return Theme.colors.video
        if (kind === "overlay") return Theme.colors.story
        if (kind === "subtitle") return Theme.colors.translate
        if (kind === "voice") return Theme.colors.info
        if (kind === "source_audio") return Theme.colors.success
        return Theme.colors.surfacePressed
    }
    function sceneIndexForX(px) {
        var clips = track.clips || []
        var scenes=[]
        for (var i=0;i<clips.length;i++) if (clips[i].sourceType === "scene_video" || clips[i].sourceType === "scene_image") scenes.push(clips[i])
        for (var j=0;j<scenes.length;j++) {
            var mid=(Number(scenes[j].startMs)+Number(scenes[j].durationMs)/2)/1000*pixelsPerSecond
            if (px < mid) return j
        }
        return Math.max(0, scenes.length-1)
    }
    Repeater {
        model: root.track.clips || []
        delegate: TimelineClip {
            required property var modelData
            clipData: modelData; pixelsPerSecond: root.pixelsPerSecond; trackLocked: !!root.track.locked
            selected: root.controller && root.controller.selectedClip.id === modelData.id
            clipColor: root.accent(root.track.type)
            onActivated: function(id) { if (root.controller) root.controller.selectClip(id) }
            onMoveDropped: function(data, xpos) {
                if (!root.controller) return
                var ms=Math.max(0,Math.round(xpos/root.pixelsPerSecond*1000)); ms=root.controller.snapTime(ms)
                if (data.sourceType === "scene_video" || data.sourceType === "scene_image") root.controller.reorderScene(data.sourceId, root.sceneIndexForX(xpos))
                else if (data.sourceType === "subtitle") root.controller.setSubtitleTiming(data.sourceId,ms,ms+Number(data.durationMs))
                else if (data.sourceType === "scene_overlay") root.controller.setOverlayTiming(data.sourceId,ms,ms+Number(data.durationMs))
            }
            onTrimRightDropped: function(data, dx) {
                if (!root.controller) return
                var delta=Math.round(dx/root.pixelsPerSecond*1000); var end=Math.max(Number(data.startMs)+100,Number(data.endMs)+delta)
                if (data.sourceType === "scene_video" || data.sourceType === "scene_image") root.controller.trimSceneRight(data.sourceId, Math.max(100,Number(data.durationMs)+delta))
                else if (data.sourceType === "subtitle") root.controller.setSubtitleTiming(data.sourceId,Number(data.startMs),end)
                else if (data.sourceType === "scene_overlay") root.controller.setOverlayTiming(data.sourceId,Number(data.startMs),end)
            }
            onTrimLeftDropped: function(data, dx) {
                if (!root.controller) return
                var delta=Math.round(dx/root.pixelsPerSecond*1000)
                if ((data.sourceType === "scene_video" || data.sourceType === "scene_image") && delta > 0) root.controller.trimSceneLeft(data.sourceId,delta)
                else if (data.sourceType === "subtitle") root.controller.setSubtitleTiming(data.sourceId,Math.max(0,Number(data.startMs)+delta),Number(data.endMs))
                else if (data.sourceType === "scene_overlay") root.controller.setOverlayTiming(data.sourceId,Math.max(0,Number(data.startMs)+delta),Number(data.endMs))
            }
            onContextRequested: function(data,gx,gy) { contextMenu.clipData=data; contextMenu.popup(gx,gy) }
        }
    }
    TimelineContextMenu { id: contextMenu; controller: root.controller }
}
