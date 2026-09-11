import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

AppCard {
    ColumnLayout {
        anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.xs
        Text { text:"Captions"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
        RowLayout { Layout.fillWidth:true
            AppComboBox { id:preset; Layout.fillWidth:true; model:["Creator","Bold","Karaoke","Clean"] }
            AppComboBox { id:words; Layout.preferredWidth:90; model:["2 words","3 words","4 words","5 words","6 words"]; currentIndex:2 }
        }
        AppButton { Layout.fillWidth:true; text:"Create Short Captions"; enabled:Shorts.workflow==="shorts" && Shorts.selectedCandidateId!==""; onClicked:Shorts.createCaptions(Shorts.selectedCandidateId,preset.currentText.toLowerCase(),words.currentIndex+2) }
        Text { Layout.fillWidth:true; text:"Word highlight uses real timestamps only. Translated captions without explicit target-word timing stay cue-level."; wrapMode:Text.WordWrap; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    }
}
