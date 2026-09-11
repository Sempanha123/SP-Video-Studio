import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"

ColumnLayout {
    id: root
    spacing: Theme.spacing.sm
    Text { text:"Speakers"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
    Repeater {
        model: VideoStudio.speakers
        delegate: Rectangle {
            required property var modelData
            Layout.fillWidth:true; implicitHeight:54; radius:Theme.radius.medium; color:Theme.colors.surfaceRaised; border.color:Theme.colors.border
            RowLayout { anchors.fill:parent; anchors.margins:8
                ColumnLayout { Layout.fillWidth:true; spacing:1
                    Text { text:modelData.name; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; font.weight:Theme.type.semibold }
                    Text { text:modelData.roleName+" · "+modelData.language+(modelData.voiceId?" · Voice assigned":" · No voice"); color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                }
                AppComboBox { id:voiceCombo; Layout.preferredWidth:150; model:VideoStudio.voices; textRole:"name"; onActivated:{ if(currentIndex>=0)VideoStudio.assignSpeakerVoice(modelData.id,VideoStudio.voices[currentIndex].id) } }
                SecondaryButton { text:"Delete"; compact:true; onClicked:VideoStudio.deleteSpeaker(modelData.id,"") }
            }
        }
    }
    RowLayout { Layout.fillWidth:true
        AppTextField { id:nameField; Layout.fillWidth:true; placeholderText:"Speaker name" }
        AppComboBox { id:roleCombo; Layout.preferredWidth:130; model:VideoStudio.speakerRoles; textRole:"name" }
        AppComboBox { id:langCombo; Layout.preferredWidth:120; model:LanguageCatalog.languages; textRole:"nativeName" }
        AppButton { text:"Add"; compact:true; onClicked:{ if(!nameField.text.trim())return; var r=roleCombo.currentIndex>=0?VideoStudio.speakerRoles[roleCombo.currentIndex].id:"speaker"; var l=langCombo.currentIndex>=0?LanguageCatalog.languages[langCombo.currentIndex].code:"en"; if(VideoStudio.addSpeaker(nameField.text.trim(),r,l,""))nameField.text="" } }
    }
}
