import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

AppCard {
    id:root
    onActiveFocusChanged: if(activeFocus && !Commands.textEditing) Commands.setContext("source_editor")
    property var timelineController
    property var selectedTranscriptIds: []
    property var transcriptRows: []
    property var ranges: []
    property var silenceRows: []

    function toggleTranscript(id, checked) {
        var next=[]
        for (var i=0;i<selectedTranscriptIds.length;i++) if (selectedTranscriptIds[i]!==id) next.push(selectedTranscriptIds[i])
        if (checked) next.push(id)
        selectedTranscriptIds=next
    }
    function addCurrentRange() {
        var meta=Shorts.settings.metadata||{}
        var a=Number(meta.inMs||0), b=Number(meta.outMs||0)
        if (b<=a) return
        var next=ranges.slice(); next.push({startMs:a,endMs:b}); ranges=next
    }

    ColumnLayout {
        anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.sm
        RowLayout {
            Layout.fillWidth:true
            Text { text:"Choose Clip"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
            Item{Layout.fillWidth:true}
            Text { text:"Manual-first"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        }
        AppComboBox { id:media; Layout.fillWidth:true; model:Shorts.mediaOptions; textRole:"name" }
        RowLayout {
            Layout.fillWidth:true
            SecondaryButton { text:"Set In"; shortcutHint:"I"; onClicked:if(root.timelineController) Shorts.setIn(root.timelineController.playheadMs) }
            SecondaryButton { text:"Set Out"; shortcutHint:"O"; onClicked:if(root.timelineController) Shorts.setOut(root.timelineController.playheadMs) }
            SecondaryButton { text:"Add Range"; compact:true; onClicked:root.addCurrentRange() }
            Text { Layout.fillWidth:true; text: "In " + (Number((Shorts.settings.metadata||{}).inMs||0)/1000).toFixed(1) + "s · Out " + (Number((Shorts.settings.metadata||{}).outMs||0)/1000).toFixed(1) + "s"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; elide:Text.ElideRight }
        }
        AppTextField { id:title; Layout.fillWidth:true; placeholderText:"Short title"; text:"New Short" }
        RowLayout {
            Layout.fillWidth:true
            AppButton { Layout.fillWidth:true; text:"Create Short Candidate"; enabled:media.currentIndex>=0; onClicked:if(media.currentIndex>=0) Shorts.createManual(Shorts.mediaOptions[media.currentIndex].id,title.text) }
            SecondaryButton { text:"Create Multi-range ("+root.ranges.length+")"; enabled:media.currentIndex>=0 && root.ranges.length>0; onClicked:{ Shorts.createMultiRange(Shorts.mediaOptions[media.currentIndex].id,root.ranges,title.text); root.ranges=[] } }
        }

        Rectangle { Layout.fillWidth:true; Layout.preferredHeight:1; color:Theme.colors.border }
        Text { text:"Transcript highlights"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
        RowLayout {
            Layout.fillWidth:true
            AppComboBox { id:transcript; Layout.fillWidth:true; model:Shorts.transcriptOptions; textRole:"label"; onActivated:{ root.transcriptRows=Shorts.transcriptSegments(Shorts.transcriptOptions[currentIndex].id); root.selectedTranscriptIds=[]; root.silenceRows=[] } }
            SecondaryButton { text:"Suggest"; compact:true; enabled:transcript.currentIndex>=0; onClicked:Shorts.suggestFromTranscript(Shorts.transcriptOptions[transcript.currentIndex].id) }
            SecondaryButton { text:"Silences"; compact:true; enabled:transcript.currentIndex>=0; onClicked:root.silenceRows=Shorts.silenceSuggestions(Shorts.transcriptOptions[transcript.currentIndex].id) }
        }
        ListView {
            Layout.fillWidth:true; Layout.preferredHeight:Math.min(126,contentHeight); clip:true; spacing:2; model:root.transcriptRows
            delegate:RowLayout { required property var modelData; width:ListView.view.width
                CheckBox { onToggled:root.toggleTranscript(String(modelData.id),checked) }
                Text { Layout.fillWidth:true; text:modelData.text||""; elide:Text.ElideRight; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                Text { text:(Number(modelData.startMs||0)/1000).toFixed(1)+"s"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            }
        }
        AppButton { Layout.fillWidth:true; visible:root.transcriptRows.length>0; text:"Create Short from Selection ("+root.selectedTranscriptIds.length+")"; enabled:root.selectedTranscriptIds.length>0 && transcript.currentIndex>=0; onClicked:Shorts.createFromTranscript(Shorts.transcriptOptions[transcript.currentIndex].id,root.selectedTranscriptIds,title.text) }
        Repeater { model:root.silenceRows
            delegate:RowLayout { required property var modelData; Layout.fillWidth:true
                Text { Layout.fillWidth:true; text:"Silence "+(Number(modelData.durationMs||0)/1000).toFixed(1)+"s"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                SecondaryButton { visible:Shorts.workflow==="shorts"; text:"Remove"; compact:true; onClicked:Shorts.applySilenceRemoval(Number(modelData.startMs),Number(modelData.endMs)) }
            }
        }

        Rectangle { Layout.fillWidth:true; Layout.preferredHeight:1; color:Theme.colors.border }
        Text { text:"Scene highlights"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
        SecondaryButton { text:"Short from all Scenes"; Layout.fillWidth:true; enabled:Shorts.sceneOptions.length>0; onClicked:{ var ids=[]; for(var i=0;i<Shorts.sceneOptions.length;i++)ids.push(Shorts.sceneOptions[i].id); Shorts.createFromScenes(ids,"Scene Short","auto") } }
        Text { Layout.fillWidth:true; text:"Suggestions use timing/scene boundaries only; they are never presented as viral scores or engagement predictions."; wrapMode:Text.WordWrap; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    }
}
