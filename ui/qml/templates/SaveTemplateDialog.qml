import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppDialog {
    id:root
    signal saveRequested(string name,string category,string description,var components,bool includeText)
    width:540; parent:Overlay.overlay; x:(parent.width-width)/2; y:(parent.height-height)/2; header:null; footer:null
    contentItem:ColumnLayout { spacing:Theme.spacing.md
        Text { text:"Save Current Setup as Template"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        InfoBanner { Layout.fillWidth:true; variant:"info"; text:"Structure only is safest. Source videos, generated narration, reference voices and News claims are excluded by default." }
        AppTextField { id:name; Layout.fillWidth:true; placeholderText:"Template name" }
        AppTextField { id:category; Layout.fillWidth:true; placeholderText:"Category (for example Creator)" }
        AppTextField { id:description; Layout.fillWidth:true; placeholderText:"Description" }
        GridLayout { columns:2; Layout.fillWidth:true
            CheckBox { id:projectSettings; text:"Project Settings"; checked:true }
            CheckBox { id:scenes; text:"Scenes / Visual Layout"; checked:true }
            CheckBox { id:speakers; text:"Speakers"; checked:true }
            CheckBox { id:speech; text:"Speech Structure"; checked:true }
            CheckBox { id:subtitles; text:"Subtitle Style"; checked:true }
            CheckBox { id:shortStyle; text:"Short Style"; checked:true }
            CheckBox { id:exportRec; text:"Export Recommendation"; checked:true }
            CheckBox { id:includeText; text:"Include script/speech text"; checked:false }
        }
        RowLayout { Layout.fillWidth:true; Item{Layout.fillWidth:true}; SecondaryButton{text:"Cancel";onClicked:root.close()}; AppButton{text:"Save Template";onClicked:{var c=[]; if(projectSettings.checked)c.push("project_settings");if(scenes.checked)c.push("scene_structure");if(speakers.checked)c.push("speaker_structure");if(speech.checked)c.push("speech_block_structure");if(subtitles.checked)c.push("subtitle_style");if(shortStyle.checked)c.push("short_style");if(exportRec.checked)c.push("export_recommendation");root.saveRequested(name.text,category.text,description.text,c,includeText.checked);root.close()}} }
    }
}
