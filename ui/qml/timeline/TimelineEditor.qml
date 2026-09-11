import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import SPVideoStudio.Phase23 1.0
import SPVideoStudio.Phase25 1.0
import SPVideoStudio.Phase30 1.0 as Phase30
import "../theme"
import "../components"
import "../editor"
import "../video"
import "../shorts"
import "../assets"
import "../audio"

FocusScope {
    id: root
    property var controller
    property var playbackController
    property string aspectRatio: "16:9"
    signal toastRequested(string message,string variant)
    signal openStoryboardRequested()
    focus: true

    Shortcut { sequence:"Ctrl+B"; onActivated:if(root.controller)root.controller.splitSelected() }
    Shortcut { sequence:"Ctrl+Z"; onActivated:if(root.controller)root.controller.undo() }
    Shortcut { sequence:"Ctrl+Y"; onActivated:if(root.controller)root.controller.redo() }
    Shortcut { sequence:"Ctrl+Shift+Z"; onActivated:if(root.controller)root.controller.redo() }
    Shortcut { sequence:"Ctrl+D"; onActivated:if(root.controller)root.controller.duplicateSelected() }
    Shortcut { sequence:"Delete"; onActivated:if(root.controller)root.controller.deleteSelected() }
    Shortcut { sequence:"M"; onActivated:if(root.controller)root.controller.addMarker("Marker") }
    Shortcut { sequence:","; onActivated:if(root.controller)root.controller.stepFrame(-1) }
    Shortcut { sequence:"."; onActivated:if(root.controller)root.controller.stepFrame(1) }
    Keys.onSpacePressed: function(event) { if(root.controller){ root.controller.togglePlayback(); event.accepted=true } }
    Keys.onLeftPressed: function(event) { if(root.controller){ root.controller.seekRelative((event.modifiers&Qt.ShiftModifier)?-5000:-500); event.accepted=true } }
    Keys.onRightPressed: function(event) { if(root.controller){ root.controller.seekRelative((event.modifiers&Qt.ShiftModifier)?5000:500); event.accepted=true } }

    property int studioPanelIndex: Shorts.workflow === "shorts" ? 1 : 0

    Component.onCompleted: {
        if (!root.controller) return
        var projectId=root.controller.currentProjectId || ""
        VideoStudio.setCurrentProject(projectId)
        Shorts.setCurrentProject(projectId)
        AssetLibrary.setCurrentProject(projectId)
        Phase30.AudioMixer.setProject(projectId, Shorts.workflow || "video")
        Phase30.AudioMixer.setTimelineState((typeof root.controller.audioClips !== "undefined" ? root.controller.audioClips : []), Number(root.controller.durationMs || 0))
        studioPanelIndex = Shorts.workflow === "shorts" ? 1 : 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.sm
        TimelineHeader { Layout.fillWidth:true; controller:root.controller }

        SplitView {
            Layout.fillWidth:true
            Layout.preferredHeight:Math.min(390,root.height*.44)
            orientation:Qt.Horizontal
            Rectangle {
                radius:Theme.radius.card; color:Theme.colors.previewBackground; border.color:Theme.colors.borderStrong
                SplitView.fillWidth:true; SplitView.minimumWidth:420
                PreviewPlayer { anchors.fill:parent; anchors.margins:Theme.spacing.sm; controller:root.playbackController }
            }
            AppCard {
                SplitView.preferredWidth:440; SplitView.minimumWidth:350
                ColumnLayout {
                    anchors.fill:parent; anchors.margins:Theme.spacing.sm; spacing:Theme.spacing.xs
                    RowLayout {
                        Layout.fillWidth:true
                        SecondaryButton { text:"Video"; compact:true; enabled:root.studioPanelIndex!==0; onClicked:root.studioPanelIndex=0 }
                        SecondaryButton { text:"Shorts"; compact:true; enabled:root.studioPanelIndex!==1; onClicked:root.studioPanelIndex=1 }
                        SecondaryButton { text:"Library"; compact:true; enabled:root.studioPanelIndex!==2; onClicked:root.studioPanelIndex=2 }
                        SecondaryButton { text:"Audio"; compact:true; enabled:root.studioPanelIndex!==3; onClicked:root.studioPanelIndex=3 }
                        Item { Layout.fillWidth:true }
                        Text { text:Shorts.workflow==="shorts"?"Short project":"Source project"; color:Theme.colors.timelineText; font.family:Theme.type.family; font.pixelSize:Theme.type.timeline }
                    }
                    StackLayout {
                        Layout.fillWidth:true; Layout.fillHeight:true; currentIndex:root.studioPanelIndex
                        UniversalVideoPanel { timelineController:root.controller }
                        ShortsStudio { timelineController:root.controller; playbackController:root.playbackController }
                        ProjectAssetPanel { workflow: Shorts.workflow || "video" }
                        AudioMixer { controller:Phase30.AudioMixer }
                    }
                }
            }
        }

        TimelineToolbar { id:toolbar; Layout.fillWidth:true; controller:root.controller; viewportWidth:timelineFlick.width }
        RowLayout {
            Layout.fillWidth:true; Layout.fillHeight:true; spacing:0
            Column {
                id: labels
                Layout.preferredWidth:174; Layout.fillHeight:true
                Rectangle {
                    width:174; height:34; color:Theme.colors.timelineRuler; border.color:Theme.colors.borderStrong
                    RowLayout { anchors.fill:parent; anchors.margins:6
                        Text { Layout.fillWidth:true; text:"TRACKS"; color:Theme.colors.timelineText; font.family:Theme.type.family; font.pixelSize:Theme.type.timeline }
                        Text { text:"Frame: , ."; color:Theme.colors.timelineText; font.family:Theme.type.family; font.pixelSize:Theme.type.timeline }
                    }
                }
                Repeater {
                    model:root.controller?root.controller.tracks:[]
                    delegate:Rectangle {
                        required property var modelData
                        width:174; height:Number(modelData.height||64); color:Theme.colors.timelineRuler; border.color:Theme.colors.borderStrong
                        RowLayout { anchors.fill:parent; anchors.margins:6; spacing:3
                            Text { Layout.fillWidth:true; text:modelData.name; elide:Text.ElideRight; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                            SecondaryButton { text:modelData.locked?"🔒":"🔓"; compact:true; onClicked:if(root.controller)root.controller.setTrackLocked(modelData.type,!modelData.locked) }
                            SecondaryButton {
                                visible:modelData.type==="voice"||modelData.type==="source_audio"||modelData.type==="music"||modelData.type==="sfx"
                                text:modelData.muted?"M":"🔊"; compact:true
                                onClicked:if(root.controller)root.controller.setTrackMuted(modelData.type,!modelData.muted)
                            }
                            SecondaryButton {
                                visible:modelData.type==="overlay"||modelData.type==="broll"||modelData.type==="video"
                                text:modelData.visible?"👁":"—"; compact:true
                                onClicked:if(root.controller)root.controller.setTrackVisible(modelData.type,!modelData.visible)
                            }
                        }
                    }
                }
            }
            Flickable {
                id: timelineFlick
                Layout.fillWidth:true; Layout.fillHeight:true; clip:true; boundsBehavior:Flickable.StopAtBounds
                contentWidth:Math.max(width,(root.controller?root.controller.durationMs/1000*root.controller.pixelsPerSecond:0)+120)
                contentHeight:timelineContent.height
                ScrollBar.horizontal:ScrollBar{}; ScrollBar.vertical:ScrollBar{}
                Item {
                    id:timelineContent; width:timelineFlick.contentWidth; height:ruler.height+trackColumn.height
                    TimelineRuler {
                        id:ruler; width:timelineContent.width; pixelsPerSecond:root.controller?root.controller.pixelsPerSecond:80; durationMs:root.controller?root.controller.durationMs:0
                        MouseArea { anchors.fill:parent; onClicked:function(mouse){ if(root.controller)root.controller.seekProject(Math.round(mouse.x/root.controller.pixelsPerSecond*1000),false) } }
                    }
                    Column {
                        id:trackColumn; y:ruler.height; width:parent.width
                        Repeater { model:root.controller?root.controller.tracks:[]; delegate:TimelineTrack { required property var modelData; track:modelData; controller:root.controller; pixelsPerSecond:root.controller?root.controller.pixelsPerSecond:80; timelineWidth:timelineContent.width } }
                    }
                    Repeater {
                        model:root.controller?root.controller.markers:[]
                        delegate:Rectangle { required property var modelData; x:Number(modelData.timeMs)/1000*(root.controller?root.controller.pixelsPerSecond:80); y:0; width:1; height:timelineContent.height; color:Theme.colors.warning; opacity:.65
                            Text { x:4; y:2; text:modelData.label; color:Theme.colors.warning; font.family:Theme.type.family; font.pixelSize:9 }
                        }
                    }
                    DropArea {
                        anchors.fill: parent
                        keys: ["sp-video-studio-media", "sp-global-asset"]
                        onDropped: function(drop) {
                            if (!drop.source || !root.controller) return
                            var projectMs=Math.max(0,Math.round(drop.x/root.controller.pixelsPerSecond*1000))
                            var subtype=drop.source.assetSubtype || ""
                            var track=drop.source.mediaType === "audio" ? (subtype === "sfx" ? "sfx" : "music") : (root.controller.durationMs<=0 ? "video" : "broll")
                            if (drop.source.assetId) {
                                AssetLibrary.setCurrentProject(root.controller.currentProjectId||"")
                                var result=AssetLibrary.addAtPlayhead(drop.source.assetId,projectMs,track)
                                if (result) drop.acceptProposedAction()
                            } else if (drop.source.mediaId && VideoStudio.addMediaAtPlayhead(drop.source.mediaId,track,projectMs)) drop.acceptProposedAction()
                        }
                    }
                    TimelinePlayhead { height:timelineContent.height; playheadMs:root.controller?root.controller.playheadMs:0; pixelsPerSecond:root.controller?root.controller.pixelsPerSecond:80; onSeekRequested:function(ms){ if(root.controller)root.controller.seekProject(ms,false) } }
                    Column { anchors.centerIn:parent; spacing:8; visible:root.controller&&root.controller.durationMs<=0
                        Text { anchors.horizontalCenter:parent.horizontalCenter; text:"No scenes yet. Add media from Universal Video Studio above."; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.body }
                        SecondaryButton { anchors.horizontalCenter:parent.horizontalCenter; text:"Open Storyboard"; onClicked:root.openStoryboardRequested() }
                    }
                }
            }
        }
    }

    Connections {
        target:root.controller; ignoreUnknownSignals:true
        function onTimelineChanged(){
            if (!root.controller) return
            var pid=root.controller.currentProjectId||""
            if(VideoStudio.currentProjectId!==pid) VideoStudio.setCurrentProject(pid); else VideoStudio.refresh()
            if(AssetLibrary.currentProjectId!==pid) AssetLibrary.setCurrentProject(pid)
            if(Phase30.AudioMixer.currentProjectId!==pid) Phase30.AudioMixer.setProject(pid,Shorts.workflow||"video")
            Phase30.AudioMixer.setTimelineState((typeof root.controller.audioClips !== "undefined" ? root.controller.audioClips : []), Number(root.controller.durationMs || 0))
            if(Shorts.currentProjectId!==pid) Shorts.setCurrentProject(pid); else Shorts.refresh()
        }
        function onOperationSucceeded(message){root.toastRequested(message,"success")}
        function onOperationFailed(message){root.toastRequested(message,"error")}
    }
    Connections {
        target:VideoStudio; ignoreUnknownSignals:true
        function onOperationSucceeded(message){root.toastRequested(message,"success"); if(root.controller)root.controller.refresh()}
        function onOperationFailed(message){root.toastRequested(message,"error")}
    }
    Connections {
        target:Shorts; ignoreUnknownSignals:true
        function onOperationSucceeded(message){root.toastRequested(message,"success"); if(root.controller)root.controller.refresh()}
        function onOperationFailed(message){root.toastRequested(message,"error")}
        function onShortProjectCreated(projectId){root.toastRequested("Short project created. Open it from Projects to continue editing.","success")}
    }
}
