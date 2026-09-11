import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import SPVideoStudio.ManualSpeech 1.0
import "../theme"
import "../components"
import "../speech"
ScrollView {
    id:root;property var timelineController;property var playbackController;property bool showSpeech:false;clip:true;contentWidth:availableWidth
    ColumnLayout { width:root.availableWidth;spacing:Theme.spacing.md
        PageHeader{Layout.fillWidth:true;title:"Shorts Maker";description:"Fast vertical edits with a calm, focused workflow.";actions:[SecondaryButton{text:root.showSpeech?"Hide Speech":"Speech / TTS";compact:true;onClicked:root.showSpeech=!root.showSpeech}]}
        WorkflowStepper{Layout.fillWidth:true;steps:["Hook","Reframe","Captions","Voiceover","Style","Export"];currentIndex:root.showSpeech?3:(Shorts.workflow==="shorts"?(Shorts.selectedCandidateId!==""?2:1):0);onStepRequested:function(i){if(i===3)root.showSpeech=true}}
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
