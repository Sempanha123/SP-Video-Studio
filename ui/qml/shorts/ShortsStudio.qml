import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import SPVideoStudio.ManualSpeech 1.0
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"
import "../speech"
ScrollView {
    id:root;property var timelineController;property var playbackController;property bool showSpeech:false;clip:true;contentWidth:availableWidth
    function handleCommand(commandId){
        if(root.showSpeech) return false
        var pos=root.timelineController?Number(root.timelineController.playheadMs||0):0
        if(commandId==="range.in"){Shorts.setIn(pos);return true}
        if(commandId==="range.out"){Shorts.setOut(pos);return true}
        if(commandId==="range.clear"){Shorts.setIn(0);Shorts.setOut(0);return true}
        return false
    }
    onVisibleChanged: if(visible && !root.showSpeech) Commands.setContext("source_range")
    onShowSpeechChanged: Commands.setContext(root.showSpeech?"speech_editor":"source_range")
    Connections{target:Commands;function onCommandTriggered(commandId){if(Commands.context==="source_range")root.handleCommand(commandId)}}
    ColumnLayout { width:root.availableWidth;spacing:Theme.spacing.md
        PageHeader{Layout.fillWidth:true;title:"Shorts Maker";description:"Fast vertical edits with a calm, focused workflow.";actions:[SecondaryButton{text:root.showSpeech?"Hide Speech":"Speech / TTS";compact:true;onClicked:root.showSpeech=!root.showSpeech}]}
        WorkflowStepper{Layout.fillWidth:true;steps:["Hook","Reframe","Captions","Voiceover","Style","Export"];currentIndex:root.showSpeech?3:(Shorts.workflow==="shorts"?(Shorts.selectedCandidateId!==""?2:1):0);onStepRequested:function(i){if(i===3)root.showSpeech=true}}
        RowLayout{Layout.fillWidth:true;visible:!root.showSpeech;spacing:Theme.spacing.sm
            Text{text:"Range shortcuts:";color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption}
            Text{text:"I  In   ·   O  Out   ·   X  Clear";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption}
            Item{Layout.fillWidth:true}
        }
        SpeechEditor{Layout.fillWidth:true;Layout.preferredHeight:440;visible:root.showSpeech;controller:ManualSpeech;projectId:Shorts.currentProjectId||""}
        AppCard{Layout.fillWidth:true;Layout.preferredHeight:280;visible:!root.showSpeech;color:Theme.colors.previewBackground;border.color:Theme.colors.borderStrong
            Item{anchors.centerIn:parent;width:Math.min(150,parent.width-40);height:Math.min(parent.height-24,width*16/9);Rectangle{anchors.fill:parent;color:"transparent";border.color:Theme.colors.borderStrong;radius:Theme.radius.small}Text{anchors.centerIn:parent;text:"9:16 preview";color:Theme.colors.timelineText;font.family:Theme.type.family;font.pixelSize:Theme.type.caption}}
        }
        ShortsSetup{Layout.fillWidth:true;visible:!root.showSpeech}
        ShortsSourcePicker{Layout.fillWidth:true;visible:!root.showSpeech;timelineController:root.timelineController}
        ShortCandidateList{Layout.fillWidth:true;visible:!root.showSpeech}
        ShortEditor{Layout.fillWidth:true;visible:!root.showSpeech&&Shorts.selectedCandidateId!==""}
        ShortReframePanel{Layout.fillWidth:true;visible:!root.showSpeech&&Shorts.workflow==="shorts"&&Shorts.sceneOptions.length>0}
        ShortCaptionPanel{Layout.fillWidth:true;visible:!root.showSpeech&&Shorts.workflow==="shorts"}
        ShortReadiness{Layout.fillWidth:true;visible:!root.showSpeech&&Shorts.selectedCandidateId!==""}
        Item{Layout.preferredHeight:Theme.spacing.md}
    }
}
