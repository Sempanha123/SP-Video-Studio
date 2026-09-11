import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

ColumnLayout {
    spacing:Theme.spacing.xs
    RowLayout { Layout.fillWidth:true
        Text { text:"Candidates"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
        Item{Layout.fillWidth:true}
        Text { text:Shorts.candidates.length; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    }
    ListView {
        Layout.fillWidth:true; Layout.preferredHeight:Math.min(200,contentHeight); clip:true; spacing:6; model:Shorts.candidates
        delegate:ShortCandidateCard { required property var modelData; width:ListView.view.width; candidate:modelData; isSelected:String(modelData.id)===Shorts.selectedCandidateId }
    }
}
