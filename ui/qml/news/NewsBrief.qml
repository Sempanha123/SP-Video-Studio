import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id:root; property var controller
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.md
        RowLayout { Layout.fillWidth:true; Text { Layout.fillWidth:true; text:"News Brief"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }; AppButton { text:"Create from Approved Claims"; onClicked:root.controller.createBrief() } }
        InfoBanner { Layout.fillWidth:true; variant:"info"; text:"Brief sections contain references to approved claim IDs; unsupported facts are not added." }
        ScrollView { Layout.fillWidth:true; Layout.fillHeight:true; Column { width:parent.width; spacing:Theme.spacing.sm; Repeater { model:root.controller?root.controller.briefs:[]; Rectangle { width:parent.width; height:92; radius:Theme.radius.medium; color:Theme.colors.surface2; border.color:Theme.colors.border; RowLayout { anchors.fill:parent; anchors.margins:Theme.spacing.md; ColumnLayout { Layout.fillWidth:true; Text { text:modelData.title||"News Brief"; color:Theme.colors.textPrimary; font.weight:Theme.type.semibold }; Text { text:(modelData.itemCount||0)+" sourced item(s) · "+(modelData.status||"draft"); color:Theme.colors.textMuted } }; SecondaryButton { text:"Approve"; onClicked:root.controller.setBriefStatus(modelData.id,"approved") }; AppButton { text:"Build Script"; onClicked:root.controller.buildScript(modelData.id) } } } } } }
    }
}
