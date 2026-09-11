import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"

ScrollView {
    id: root
    property var timelineController
    contentWidth: availableWidth
    ColumnLayout {
        width: root.availableWidth; spacing:Theme.spacing.md
        Text { text:"Universal Video Studio"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        Text { Layout.fillWidth:true; text:"Manual media, layered video, presenters, B-roll, voices and green screen. AI is optional."; color:Theme.colors.textSecondary; wrapMode:Text.WordWrap; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
        Text { text:"Add at Playhead"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
        AppComboBox { id:mediaCombo; Layout.fillWidth:true; model:VideoStudio.mediaItems; textRole:"name" }
        RowLayout { Layout.fillWidth:true
            AppComboBox { id:trackCombo; Layout.fillWidth:true; model:["V1 Main","V2 B-roll","V3 Presenter/Overlay","Audio"] }
            AppButton { text:"Add"; compact:true; enabled:mediaCombo.currentIndex>=0; onClicked:{ var row=VideoStudio.mediaItems[mediaCombo.currentIndex]; var tracks=["video","broll","overlay","music"]; VideoStudio.addMediaAtPlayhead(row.id,tracks[trackCombo.currentIndex],root.timelineController?root.timelineController.playheadMs:0) } }
        }
        Text { text:"Scene"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
        AppComboBox { id:sceneCombo; Layout.fillWidth:true; model:VideoStudio.scenes; textRole:"name"; onActivated:if(currentIndex>=0)VideoStudio.selectScene(VideoStudio.scenes[currentIndex].id) }
        Text { text:"Layers"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
        AppComboBox { id:layerCombo; Layout.fillWidth:true; model:VideoStudio.layers; textRole:"role"; onActivated:if(currentIndex>=0)VideoStudio.selectLayer(VideoStudio.layers[currentIndex].id) }
        RowLayout { Layout.fillWidth:true
            AppComboBox { id:roleCombo; Layout.fillWidth:true; model:VideoStudio.visualRoles; textRole:"name" }
            AppButton { text:"Add Layer"; compact:true; enabled:mediaCombo.currentIndex>=0 && VideoStudio.selectedSceneId!==""; onClicked:{ var m=VideoStudio.mediaItems[mediaCombo.currentIndex]; var r=VideoStudio.visualRoles[roleCombo.currentIndex].id; VideoStudio.addLayer(m.id,r,r==="presenter"||r==="reporter"?"bottom_right":"") } }
        }
        VisualLayerInspector { Layout.fillWidth:true }
        Rectangle { Layout.fillWidth:true; Layout.preferredHeight:1; color:Theme.colors.border }
        SpeakerManager { Layout.fillWidth:true }
        Rectangle { Layout.fillWidth:true; Layout.preferredHeight:1; color:Theme.colors.border }
        SpeechBlockEditor { Layout.fillWidth:true }
        Item { Layout.preferredHeight:12 }
    }
}
