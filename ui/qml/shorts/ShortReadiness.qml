import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

AppCard {
    property var r:Shorts.readiness
    ColumnLayout {
        anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.xs
        RowLayout { Layout.fillWidth:true
            Text { Layout.fillWidth:true; text:"Readiness"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
            StatusBadge { text:r.status||"Not Ready"; status:r.status==="Ready"?"success":(r.status==="Needs Review"?"warning":"neutral") }
        }
        Text { text:"Aspect  "+String(r.aspect||Shorts.settings.targetAspectRatio||"9:16"); color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        Text { text:"Captions  "+String(r.captions||"Optional")+" · Audio  "+String(r.audio||"Check")+" · Visuals  "+String(r.visuals||"Check"); color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; wrapMode:Text.WordWrap; Layout.fillWidth:true }
        Text { visible:Shorts.selectedCandidateId!==""; text:"Recommended export preset: "+Shorts.recommendedExportPreset(); color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    }
}
