import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"
import "../editor"
import "../video"

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

    Component.onCompleted: if(root.controller) VideoStudio.setCurrentProject(root.controller.currentProjectId || "")

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.sm
        TimelineHeader { Layout.fillWidth:true; controller:root.controller }

        SplitView {
            Layout.fillWidth:true
            Layout.preferredHeight:Math.min(390,root.height*.44)
            orientation:Qt.Horizontal
            AppCard {
                SplitView.fillWidth:true; SplitView.minimumWidth:420
                PreviewPlayer { anchors.fill:parent; anchors.margins:Theme.spacing.sm; controller:root.playbackController }
            }
            AppCard {
                SplitView.preferredWidth:420; SplitView.minimumWidth:340
                UniversalVideoPanel { anchors.fill:parent; anchors.margins:Theme.spacing.md; timelineController:root.controller }
            }
        }

        TimelineToolbar { id:toolbar; Layout.fillWidth:true; controller:root.controller; viewportWidth:timelineFlick.width }
        RowLayout {
            Layout.fillWidth:true; Layout.fillHeight:true; spacing:0
            Column {
                id: labels
                Layout.preferredWidth:174; Layout.fillHeight:true
                Rectangle {
                    width:174; height:34; color:Theme.colors.surfaceRaised; border.color:Theme.colors.border
                    RowLayout { anchors.fill:parent; anchors.margins:6
                        Text { Layout.fillWidth:true; text:"TRACKS"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                        Text { text:"Frame: , ."; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:9 }
                    }
                }
                Repeater {
                    model:root.controller?root.controller.tracks:[]
                    delegate:Rectangle {
                        required property var modelData
                        width:174; height:Number(modelData.height||64); color:Theme.colors.surfaceRaised; border.color:Theme.colors.border
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
                        keys: ["sp-video-studio-media"]
                        onDropped: function(drop) {
                            if (!drop.source || !drop.source.mediaId || !root.controller) return
                            var projectMs=Math.max(0,Math.round(drop.x/root.controller.pixelsPerSecond*1000))
                            var track=drop.source.mediaType === "audio" ? "music" : (root.controller.durationMs<=0 ? "video" : "broll")
                            if (VideoStudio.addMediaAtPlayhead(drop.source.mediaId,track,projectMs)) drop.acceptProposedAction()
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
        function onTimelineChanged(){ if(root.controller && VideoStudio.currentProjectId!==root.controller.currentProjectId) VideoStudio.setCurrentProject(root.controller.currentProjectId||""); else VideoStudio.refresh() }
        function onOperationSucceeded(message){root.toastRequested(message,"success")}
        function onOperationFailed(message){root.toastRequested(message,"error")}
    }
    Connections {
        target:VideoStudio; ignoreUnknownSignals:true
        function onOperationSucceeded(message){root.toastRequested(message,"success"); if(root.controller)root.controller.refresh()}
        function onOperationFailed(message){root.toastRequested(message,"error")}
    }
}
