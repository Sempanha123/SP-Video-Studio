import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
import "../editor"

FocusScope {
    id: root
    property var controller
    property var playbackController
    property string aspectRatio: "16:9"
    signal toastRequested(string message,string variant)
    signal openStoryboardRequested()
    focus:true
    Shortcut { sequence:"Ctrl+B"; onActivated:if(root.controller)root.controller.splitSelected() }
    Shortcut { sequence:"Ctrl+Z"; onActivated:if(root.controller)root.controller.undo() }
    Shortcut { sequence:"Ctrl+Y"; onActivated:if(root.controller)root.controller.redo() }
    Shortcut { sequence:"Ctrl+Shift+Z"; onActivated:if(root.controller)root.controller.redo() }
    Shortcut { sequence:"Ctrl+D"; onActivated:if(root.controller)root.controller.duplicateSelected() }
    Shortcut { sequence:"Delete"; onActivated:if(root.controller)root.controller.deleteSelected() }
    Shortcut { sequence:"M"; onActivated:if(root.controller)root.controller.addMarker("Marker") }
    Keys.onSpacePressed: function(event) { if (root.controller) { root.controller.togglePlayback(); event.accepted=true } }
    Keys.onLeftPressed: function(event) { if(root.controller){ root.controller.seekRelative((event.modifiers & Qt.ShiftModifier)?-5000:-500); event.accepted=true } }
    Keys.onRightPressed: function(event) { if(root.controller){ root.controller.seekRelative((event.modifiers & Qt.ShiftModifier)?5000:500); event.accepted=true } }

    ColumnLayout {
        anchors.fill:parent; spacing:Theme.spacing.sm
        TimelineHeader { Layout.fillWidth:true; controller:root.controller }
        SplitView {
            Layout.fillWidth:true; Layout.preferredHeight:Math.min(330,root.height*.38); orientation:Qt.Horizontal
            AppCard {
                SplitView.fillWidth:true; SplitView.minimumWidth:460
                PreviewPlayer { anchors.fill:parent; anchors.margins:Theme.spacing.sm; controller:root.playbackController }
            }
            AppCard {
                SplitView.preferredWidth:340; SplitView.minimumWidth:300
                ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.sm
                    Text { text:"Clip Inspector"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
                    Text { Layout.fillWidth:true; text: root.controller && root.controller.selectedClip.id ? (root.controller.selectedClip.label || root.controller.selectedClip.sourceType) : "Select a timeline clip"; color:Theme.colors.textSecondary; wrapMode:Text.WordWrap; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
                    Text { visible:root.controller && root.controller.selectedClip.id; text: root.controller ? ((root.controller.selectedClip.startMs/1000).toFixed(2)+"s → "+(root.controller.selectedClip.endMs/1000).toFixed(2)+"s") : ""; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                    RowLayout { visible:root.controller && (root.controller.selectedClip.sourceType === "narration" || root.controller.selectedClip.sourceType === "source_audio"); Text { text:"Volume"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall } Slider { id:audioVolume; Layout.fillWidth:true; from:0; to:100; value: root.controller && root.controller.selectedClip.metadata ? Number(root.controller.selectedClip.metadata.volume||1)*100 : 100; onPressedChanged:{ if(pressed || !root.controller)return; if(root.controller.selectedClip.sourceType === "narration") root.controller.setNarrationVolume(root.controller.selectedClip.sourceId,Math.round(value)); else root.controller.setSourceAudioVolume(root.controller.selectedClip.sourceId,Math.round(value)) } } SecondaryButton { text: root.controller && root.controller.selectedClip.enabled === false ? "Unmute" : "Mute"; compact:true; onClicked:{ if(!root.controller)return; var mute=root.controller.selectedClip.enabled !== false; if(root.controller.selectedClip.sourceType === "narration")root.controller.setNarrationMuted(root.controller.selectedClip.sourceId,mute); else root.controller.setSourceAudioMuted(root.controller.selectedClip.sourceId,mute) } } }
                    ColumnLayout { Layout.fillWidth:true; visible:root.controller && (root.controller.selectedClip.sourceType === "scene_video" || root.controller.selectedClip.sourceType === "scene_image"); spacing:4
                        Text { text:"Transition Out"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
                        RowLayout { spacing:4
                            SecondaryButton { text:"Cut"; compact:true; onClicked:if(root.controller)root.controller.setTransition(root.controller.selectedClip.sourceId,"cut",0) }
                            SecondaryButton { text:"Fade"; compact:true; onClicked:if(root.controller)root.controller.setTransition(root.controller.selectedClip.sourceId,"fade",Math.max(100,Number(root.controller.selectedClip.metadata.transitionDurationMs||300))) }
                            SecondaryButton { text:"Cross"; compact:true; onClicked:if(root.controller)root.controller.setTransition(root.controller.selectedClip.sourceId,"crossfade",Math.max(100,Number(root.controller.selectedClip.metadata.transitionDurationMs||300))) }
                            SecondaryButton { text:"Slide"; compact:true; onClicked:if(root.controller)root.controller.setTransition(root.controller.selectedClip.sourceId,"slide",Math.max(100,Number(root.controller.selectedClip.metadata.transitionDurationMs||300))) }
                        }
                        RowLayout { Layout.fillWidth:true; visible:root.controller && root.controller.selectedClip.metadata && root.controller.selectedClip.metadata.transitionType !== "cut"
                            Text { text:"Duration"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                            Slider { id:transitionDuration; Layout.fillWidth:true; from:100; to:2000; stepSize:50; value: root.controller && root.controller.selectedClip.metadata ? Math.max(100,Number(root.controller.selectedClip.metadata.transitionDurationMs||300)) : 300; onPressedChanged:{ if(!pressed && root.controller)root.controller.setTransition(root.controller.selectedClip.sourceId,String(root.controller.selectedClip.metadata.transitionType||"fade"),Math.round(value)) } }
                            Text { text:Math.round(transitionDuration.value)+" ms"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                        }
                    }
                    RowLayout { visible:root.controller && (root.controller.selectedClip.sourceType === "scene_video" || root.controller.selectedClip.sourceType === "scene_image"); SecondaryButton { text:"Split"; compact:true; onClicked:root.controller.splitSelected() } SecondaryButton { text:"Duplicate"; compact:true; onClicked:root.controller.duplicateSelected() } }
                    Item { Layout.fillHeight:true }
                    Text { Layout.fillWidth:true; visible:root.controller && root.controller.issues.length>0; text:root.controller ? root.controller.issues.length+" timeline warning(s)" : ""; color:Theme.colors.warning; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                }
            }
        }
        TimelineToolbar { id:toolbar; Layout.fillWidth:true; controller:root.controller; viewportWidth:timelineFlick.width }
        RowLayout {
            Layout.fillWidth:true; Layout.fillHeight:true; spacing:0
            Column {
                id:labels; Layout.preferredWidth:150; Layout.fillHeight:true
                Rectangle { width:150; height:34; color:Theme.colors.surfaceRaised; border.color:Theme.colors.border; Text { anchors.centerIn:parent; text:"TRACKS"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption } }
                Repeater { model:root.controller ? root.controller.tracks : []; delegate:Rectangle { required property var modelData; width:150; height:Number(modelData.height||64); color:Theme.colors.surfaceRaised; border.color:Theme.colors.border
                    RowLayout { anchors.fill:parent; anchors.margins:6; spacing:4
                        Text { Layout.fillWidth:true; text:modelData.name; elide:Text.ElideRight; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                        SecondaryButton { text:modelData.locked?"🔒":"🔓"; compact:true; onClicked:if(root.controller)root.controller.setTrackLocked(modelData.type,!modelData.locked) }
                        SecondaryButton { visible:modelData.type==="voice" || modelData.type==="source_audio"; text:modelData.muted?"Muted":"Mute"; compact:true; onClicked:if(root.controller)root.controller.setTrackMuted(modelData.type,!modelData.muted) }
                        SecondaryButton { visible:modelData.type==="overlay"; text:modelData.visible?"Eye":"Hidden"; compact:true; onClicked:if(root.controller)root.controller.setTrackVisible(modelData.type,!modelData.visible) }
                    }
                } }
            }
            Flickable {
                id:timelineFlick; Layout.fillWidth:true; Layout.fillHeight:true; clip:true; boundsBehavior:Flickable.StopAtBounds
                contentWidth:Math.max(width, (root.controller ? root.controller.durationMs/1000*root.controller.pixelsPerSecond : 0)+120)
                contentHeight:timelineContent.height
                ScrollBar.horizontal:ScrollBar{}; ScrollBar.vertical:ScrollBar{}
                Item {
                    id:timelineContent; width:timelineFlick.contentWidth; height:ruler.height+trackColumn.height
                    TimelineRuler { id:ruler; width:timelineContent.width; pixelsPerSecond:root.controller ? root.controller.pixelsPerSecond : 80; durationMs:root.controller ? root.controller.durationMs : 0
                        MouseArea { anchors.fill:parent; onClicked:function(mouse){ if(root.controller)root.controller.seekProject(Math.round(mouse.x/root.controller.pixelsPerSecond*1000),false) } }
                    }
                    Column { id:trackColumn; y:ruler.height; width:parent.width
                        Repeater { model:root.controller ? root.controller.tracks : []; delegate:TimelineTrack { required property var modelData; track:modelData; controller:root.controller; pixelsPerSecond:root.controller ? root.controller.pixelsPerSecond : 80; timelineWidth:timelineContent.width } }
                    }
                    Repeater { model:root.controller ? root.controller.markers : []; delegate:Rectangle { required property var modelData; x:Number(modelData.timeMs)/1000*(root.controller?root.controller.pixelsPerSecond:80); y:0; width:1; height:timelineContent.height; color:Theme.colors.warning; opacity:.65; Text { x:4; y:2; text:modelData.label; color:Theme.colors.warning; font.family:Theme.type.family; font.pixelSize:9 } } }
                    TimelinePlayhead { height:timelineContent.height; playheadMs:root.controller ? root.controller.playheadMs : 0; pixelsPerSecond:root.controller ? root.controller.pixelsPerSecond : 80; onSeekRequested:function(ms){ if(root.controller)root.controller.seekProject(ms,false) } }
                    Column { anchors.centerIn:parent; spacing:8; visible:root.controller && root.controller.durationMs <= 0
                        Text { anchors.horizontalCenter:parent.horizontalCenter; text:"No scenes yet."; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.body }
                        SecondaryButton { anchors.horizontalCenter:parent.horizontalCenter; text:"Open Storyboard"; onClicked:root.openStoryboardRequested() }
                    }
                }
            }
        }
    }
    Connections { target:root.controller; ignoreUnknownSignals:true; function onOperationSucceeded(message){root.toastRequested(message,"success")} function onOperationFailed(message){root.toastRequested(message,"error")} }
}
