import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

ScrollView {
    id:root
    property var timelineController
    property var playbackController
    clip:true
    contentWidth:availableWidth
    ColumnLayout {
        width:root.availableWidth; spacing:Theme.spacing.sm
        RowLayout { Layout.fillWidth:true
            ColumnLayout { Layout.fillWidth:true; spacing:1
                Text { text:"Shorts Maker"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
                Text { text:"Choose Clip → Reframe → Caption → Polish → Export"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            }
            StatusBadge { text:Shorts.workflow==="shorts"?"Short Project":"Source Project"; status:Shorts.workflow==="shorts"?"success":"neutral" }
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
