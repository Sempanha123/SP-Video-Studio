import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"

ColumnLayout {
    id:root; spacing:Theme.spacing.sm
    Text { text:"Dialogue / Speech Blocks"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
    Repeater {
        model:VideoStudio.speechBlocks
        delegate:Rectangle {
            required property var modelData
            Layout.fillWidth:true; implicitHeight:72; radius:Theme.radius.medium; color:Theme.colors.surfaceRaised; border.color:Theme.colors.border
            ColumnLayout { anchors.fill:parent; anchors.margins:8; spacing:2
                Text { Layout.fillWidth:true; text:(modelData.language||"en").toUpperCase()+" · "+(modelData.speakerId?"Speaker assigned":"Narration/default"); color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                Text { Layout.fillWidth:true; text:modelData.text; elide:Text.ElideRight; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
            }
        }
    }
    Text { visible:VideoStudio.scriptSections.length===0; text:"Script is optional. Create/open Script only when you want dialogue or TTS."; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; wrapMode:Text.WordWrap }
    ColumnLayout { Layout.fillWidth:true; visible:VideoStudio.scriptSections.length>0
        AppComboBox { id:sectionCombo; Layout.fillWidth:true; model:VideoStudio.scriptSections; textRole:"title" }
        AppTextField { id:textField; Layout.fillWidth:true; placeholderText:"Spoken text" }
        RowLayout { Layout.fillWidth:true
            AppComboBox { id:speakerCombo; Layout.fillWidth:true; model:VideoStudio.speakers; textRole:"name" }
            AppComboBox { id:languageCombo; Layout.preferredWidth:130; model:LanguageCatalog.languages; textRole:"nativeName" }
            AppButton { text:"Add Dialogue"; compact:true; enabled:textField.text.trim().length>0; onClicked:{ var sec=VideoStudio.scriptSections[sectionCombo.currentIndex]; var speaker=speakerCombo.currentIndex>=0?VideoStudio.speakers[speakerCombo.currentIndex]:({}); var lang=languageCombo.currentIndex>=0?LanguageCatalog.languages[languageCombo.currentIndex].code:(sec.language||"en"); if(VideoStudio.addDialogue(sec.id,textField.text,speaker.id||"",lang))textField.text="" } }
        }
    }
}
