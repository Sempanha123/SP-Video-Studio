import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item { id:root; property var readiness
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        SectionHeader { title:"Production Readiness"; subtitle:(root.readiness.level||"not_ready").replace(/_/g," ") }
        GridLayout { Layout.fillWidth:true; columns:3; columnSpacing:Theme.spacing.md; rowSpacing:Theme.spacing.md
            AppCard { Layout.fillWidth:true; implicitHeight:100; Column { anchors.centerIn:parent; Text{text:(root.readiness.beatCount||0)+" Beats";color:Theme.colors.textPrimary;font.weight:Theme.type.semibold};Text{text:"Outline: "+(root.readiness.outlineStatus||"missing");color:Theme.colors.textMuted} } }
            AppCard { Layout.fillWidth:true; implicitHeight:100; Column { anchors.centerIn:parent; Text{text:Math.round((root.readiness.estimatedDurationMs||0)/1000)+" sec";color:Theme.colors.textPrimary;font.weight:Theme.type.semibold};Text{text:"Estimated narration";color:Theme.colors.textMuted} } }
            AppCard { Layout.fillWidth:true; implicitHeight:100; Column { anchors.centerIn:parent; Text{text:(root.readiness.sceneCount||0)+" Scenes";color:Theme.colors.textPrimary;font.weight:Theme.type.semibold};Text{text:(root.readiness.subtitleCount||0)+" subtitle track(s)";color:Theme.colors.textMuted} } }
        }
        Repeater { model:root.readiness.issues||[]; InfoBanner { Layout.fillWidth:true; text:modelData.message } }
    }
}
