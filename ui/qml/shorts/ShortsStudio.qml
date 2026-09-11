import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"
ScrollView {
    id:root; property var timelineController; property var playbackController; clip:true; contentWidth:availableWidth
    ColumnLayout { width:root.availableWidth; spacing:Theme.spacing.md
        PageHeader { Layout.fillWidth:true; title:"Shorts Maker"; description:"Fast vertical edits with a calm, focused workflow." }
        WorkflowStepper { Layout.fillWidth:true; steps:["Hook","Reframe","Captions","Style","Export"]; currentIndex: Shorts.workflow === "shorts" ? (Shorts.selectedCandidateId !== "" ? 2 : 1) : 0 }
        AppCard { Layout.fillWidth:true; Layout.preferredHeight:280; color:Theme.colors.previewBackground; border.color:Theme.colors.borderStrong
            Item { anchors.centerIn:parent; width:Math.min(150,parent.width-40); height:Math.min(parent.height-24,width*16/9)
                Rectangle { anchors.fill:parent; color:"transparent"; border.color:Theme.colors.borderStrong; radius:Theme.radius.small }
                Text { anchors.centerIn:parent; text:"9:16 preview"; color:Theme.colors.timelineText; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            }
        }
        ShortsSetup { Layout.fillWidth:true }
        ShortsSourcePicker { Layout.fillWidth:true; timelineController:root.timelineController }
        ShortCandidateList { Layout.fillWidth:true }
        ShortEditor { Layout.fillWidth:true; visible:Shorts.selectedCandidateId!=="" }
        ShortReframePanel { Layout.fillWidth:true; visible:Shorts.workflow==="shorts" && Shorts.sceneOptions.length>0 }
        ShortCaptionPanel { Layout.fillWidth:true; visible:Shorts.workflow==="shorts" }
        ShortReadiness { Layout.fillWidth:true; visible:Shorts.selectedCandidateId!=="" }
        Item { Layout.preferredHeight:Theme.spacing.md }
    }
}
