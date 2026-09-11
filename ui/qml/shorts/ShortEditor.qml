import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

AppCard {
    property var c:Shorts.selectedCandidate
    ColumnLayout {
        anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.xs
        Text { text:"Polish"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
        AppTextField { id:title; Layout.fillWidth:true; placeholderText:"Title"; text:c.title||"" }
        AppTextField { id:hook; Layout.fillWidth:true; placeholderText:"Optional hook / headline"; text:c.hook||"" }
        RowLayout { Layout.fillWidth:true
            SecondaryButton { text:"Save"; enabled:Shorts.selectedCandidateId!==""; onClicked:Shorts.editCandidate(Shorts.selectedCandidateId,title.text,hook.text) }
            SecondaryButton { text:"Duplicate"; enabled:Shorts.selectedCandidateId!==""; onClicked:Shorts.duplicateCandidate(Shorts.selectedCandidateId) }
            Item{Layout.fillWidth:true}
            AppButton { text:Shorts.workflow==="shorts"?"Independent Short":"Create Editable Short"; enabled:Shorts.selectedCandidateId!=="" && Shorts.workflow!=="shorts"; onClicked:Shorts.createEditableShort(Shorts.selectedCandidateId) }
        }
        Text { Layout.fillWidth:true; text:"Hooks are user-authored or copied from approved source text. Shorts Maker does not invent unsupported News claims."; wrapMode:Text.WordWrap; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    }
}
