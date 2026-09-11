import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

AppCard {
    id:root
    property var candidate: ({})
    property bool isSelected:false
    interactive:true
    onClicked:Shorts.selectCandidate(candidate.id||"")
    selected:root.isSelected
    ColumnLayout {
        anchors.fill:parent; anchors.margins:Theme.spacing.sm; spacing:2
        RowLayout { Layout.fillWidth:true
            Text { Layout.fillWidth:true; text:candidate.title||"Short"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; font.weight:Theme.type.semibold; elide:Text.ElideRight }
            StatusBadge { text:candidate.status||"draft"; status:candidate.status==="outdated"?"warning":"neutral" }
        }
        Text { text:(Number(candidate.durationMs||0)/1000).toFixed(1)+" sec · "+String(candidate.sourceType||""); color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        Text { visible:!!candidate.hook; Layout.fillWidth:true; text:candidate.hook||""; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; elide:Text.ElideRight }
    }
}
